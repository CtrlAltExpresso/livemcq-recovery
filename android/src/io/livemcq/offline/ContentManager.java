package io.livemcq.offline;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.StatFs;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * Downloads the chunked content bundle (manifest + .zip parts), verifies each
 * part's sha256 and extracts it under the internal files dir. Downloads use
 * HTTP Range resume into a temp file that survives restarts, so an
 * interrupted sync resumes where it stopped. Thread-safe listener callbacks
 * arrive on worker threads; the caller should marshal to the UI thread.
 */
public final class ContentManager {

    public interface Listener {
        void onProgress(long doneBytes, long totalBytes, String detail);
        void onError(String message);
        void onDone();
    }

    private static final int WORKERS = 3;
    private static final int MAX_PART_RETRIES = 4;
    private static final String PREFS = "livemcq";
    private static final String KEY_URL = "manifest_url";
    private static final String KEY_READY = "content_ready";

    private final Context ctx;
    private final File root;
    private final SharedPreferences prefs;
    private final AtomicBoolean cancelled = new AtomicBoolean();
    private final AtomicLong downloaded = new AtomicLong();
    private final AtomicInteger nextPart = new AtomicInteger();
    private ExecutorService pool;

    public ContentManager(Context ctx) {
        this.ctx = ctx.getApplicationContext();
        this.root = new File(this.ctx.getFilesDir(), "content");
        this.prefs = this.ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public File contentRoot() {
        return root;
    }

    public boolean isReady() {
        return prefs.getBoolean(KEY_READY, false) && new File(root, ".ready").exists();
    }

    public String savedUrl() {
        return prefs.getString(KEY_URL, "");
    }

    public long freeMegabytes() {
        StatFs sf = new StatFs(ctx.getFilesDir().getAbsolutePath());
        long bytes = (long) sf.getAvailableBlocks() * sf.getBlockSize();
        return bytes / (1024 * 1024);
    }

    public void cancel() {
        cancelled.set(true);
    }

    public void sync(final String manifestUrl, final Listener listener) {
        cancelled.set(false);
        new Thread(() -> run(manifestUrl, listener), "content-sync").start();
    }

    private void run(String manifestUrl, Listener listener) {
        try {
            JSONObject manifest = fetchJson(manifestUrl.trim());
            if (manifest == null) {
                listener.onError("Could not read the manifest. Check the URL.");
                return;
            }
            JSONArray parts = manifest.optJSONArray("parts");
            if (parts == null || parts.length() == 0) {
                listener.onError("Manifest has no parts.");
                return;
            }
            long totalBytes = Math.max(manifest.optLong("total_bytes", 0), 1);
            String base = manifestUrl.substring(0, manifestUrl.lastIndexOf('/') + 1);

            long neededMB = totalBytes / (1024 * 1024) + 2048;
            if (freeMegabytes() < neededMB) {
                listener.onError(String.format(Locale.US,
                        "Not enough free space (have %.1f GB, need ~%.1f GB). Free up space, then retry.",
                        freeMegabytes() / 1024.0, neededMB / 1024.0));
                return;
            }

            root.mkdirs();
            prefs.edit().putString(KEY_URL, manifestUrl).apply();
            downloaded.set(0);
            nextPart.set(0);

            AtomicInteger completed = new AtomicInteger();
            pool = Executors.newFixedThreadPool(WORKERS);
            for (int w = 0; w < WORKERS; w++) {
                pool.execute(() -> {
                    while (!cancelled.get()) {
                        int i = nextPart.getAndIncrement();
                        if (i >= parts.length()) {
                            return;
                        }
                        JSONObject part = parts.optJSONObject(i);
                        String file = part != null ? part.optString("file") : null;
                        if (file == null || file.isEmpty()) {
                            continue;
                        }
                        String sha = part.optString("sha256");
                        long size = part.optLong("size", 0);
                        if (!process(base + file, file, sha, size, listener)) {
                            if (!cancelled.get()) {
                                listener.onError("Download failed: " + file);
                            }
                            cancelled.set(true);
                            return;
                        }
                        completed.incrementAndGet();
                        progress(listener, downloaded.get(), totalBytes, completed.get(), parts.length());
                    }
                });
            }
            pool.shutdown();
            pool.awaitTermination(8, TimeUnit.HOURS);
            if (cancelled.get() || completed.get() != parts.length()) {
                return;
            }
            writeMarker();
            prefs.edit().putBoolean(KEY_READY, true).apply();
            listener.onDone();
        } catch (Exception e) {
            listener.onError("Unexpected error: " + e.getMessage());
        } finally {
            if (pool != null) {
                pool.shutdownNow();
            }
        }
    }

    private boolean process(String partUrl, String file, String sha, long size, Listener listener) {
        File tmp = new File(root, file + ".part");
        for (int attempt = 0; attempt < MAX_PART_RETRIES; attempt++) {
            if (cancelled.get()) {
                return false;
            }
            try {
                long have = tmp.exists() ? tmp.length() : 0;
                if (have < size || !valid(tmp, sha)) {
                    download(partUrl, tmp, size, have, listener);
                }
                if (!valid(tmp, sha)) {
                    tmp.delete();
                    continue;
                }
                extract(tmp);
                downloaded.addAndGet(tmp.length());
                tmp.delete();
                return true;
            } catch (IOException e) {
                tmp.delete();
                if (cancelled.get()) {
                    return false;
                }
                listener.onProgress(-1, -1, "Retrying " + file + " (" + (attempt + 1) + ")");
            }
        }
        return false;
    }

    private void download(String partUrl, File tmp, long size, long have, Listener listener) throws IOException {
        HttpURLConnection conn = null;
        InputStream in = null;
        OutputStream out = null;
        try {
            try {
                conn = (HttpURLConnection) new URI(partUrl).toURL().openConnection();
            } catch (java.net.URISyntaxException e) {
                throw new IOException("bad URL: " + partUrl);
            }
            conn.setInstanceFollowRedirects(true);
            conn.setConnectTimeout(20000);
            conn.setReadTimeout(45000);
            conn.setRequestProperty("User-Agent", "LiveMCQ-Recovery/1.0");
            conn.setRequestProperty("Range", "bytes=" + have + "-");
            int code = conn.getResponseCode();
            if (code != 200 && code != 206) {
                throw new IOException("HTTP " + code);
            }
            in = new BufferedInputStream(conn.getInputStream(), 256 * 1024);
            out = new BufferedOutputStream(new FileOutputStream(tmp, true), 256 * 1024);
            byte[] buf = new byte[128 * 1024];
            int r;
            while ((r = in.read(buf)) > 0) {
                if (cancelled.get()) {
                    throw new IOException("cancelled");
                }
                out.write(buf, 0, r);
                if (size > 0 && (r % (buf.length * 8)) == 0) {
                    listener.onProgress(-1, -1,
                            String.format(Locale.US, "%.1f / %.1f MB  %s",
                                    tmp.length() / 1048576.0, size / 1048576.0, tmp.getName()));
                }
            }
            out.flush();
        } finally {
            try { if (in != null) in.close(); } catch (IOException ignored) {}
            try { if (out != null) out.close(); } catch (IOException ignored) {}
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    private boolean valid(File f, String sha) {
        if (sha == null || sha.isEmpty()) {
            return true;
        }
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            try (InputStream in = new BufferedInputStream(new FileInputStream(f), 256 * 1024)) {
                byte[] buf = new byte[128 * 1024];
                int r;
                while ((r = in.read(buf)) > 0) {
                    md.update(buf, 0, r);
                }
            }
            StringBuilder sb = new StringBuilder(64);
            for (byte b : md.digest()) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString().equalsIgnoreCase(sha);
        } catch (IOException | NoSuchAlgorithmException e) {
            return false;
        }
    }

    private void extract(File part) throws IOException {
        try (ZipInputStream zin = new ZipInputStream(new BufferedInputStream(new FileInputStream(part), 256 * 1024))) {
            ZipEntry e;
            while ((e = zin.getNextEntry()) != null) {
                if (cancelled.get()) {
                    throw new IOException("cancelled");
                }
                if (!e.isDirectory()) {
                    File target = safe(root, e.getName());
                    File parent = target.getParentFile();
                    if (parent != null && !parent.exists() && !parent.mkdirs() && !parent.isDirectory()) {
                        throw new IOException("cannot create " + parent);
                    }
                    try (OutputStream fout = new BufferedOutputStream(new FileOutputStream(target), 128 * 1024)) {
                        byte[] buf = new byte[128 * 1024];
                        int r;
                        while ((r = zin.read(buf)) > 0) {
                            if (cancelled.get()) {
                                throw new IOException("cancelled");
                            }
                            fout.write(buf, 0, r);
                        }
                        fout.flush();
                    }
                }
                zin.closeEntry();
            }
        }
    }

    private static File safe(File root, String name) throws IOException {
        File target = root;
        for (String seg : name.split("/")) {
            if (seg.isEmpty() || seg.equals(".")) {
                continue;
            }
            if (seg.equals("..")) {
                throw new IOException("bad path");
            }
            target = new File(target, seg);
        }
        return target;
    }

    private static String name(String file) {
        int i = file.lastIndexOf('/');
        return i >= 0 ? file.substring(i + 1) : file;
    }

    private void writeMarker() throws IOException {
        File m = new File(root, ".ready");
        try (OutputStream out = new FileOutputStream(m)) {
            out.write("ok\n".getBytes("UTF-8"));
        }
    }

    private JSONObject fetchJson(String url) {
        String s = fetch(url);
        if (s == null) {
            return null;
        }
        try {
            return new JSONObject(s);
        } catch (Exception e) {
            return null;
        }
    }

    private String fetch(String url) {
        HttpURLConnection conn = null;
        try {
            conn = (HttpURLConnection) new URI(url).toURL().openConnection();
            conn.setInstanceFollowRedirects(true);
            conn.setConnectTimeout(20000);
            conn.setReadTimeout(45000);
            conn.setRequestProperty("User-Agent", "LiveMCQ-Recovery/1.0");
            if (conn.getResponseCode() != 200) {
                return null;
            }
            try (java.io.ByteArrayOutputStream bos = new java.io.ByteArrayOutputStream();
                 InputStream in = conn.getInputStream()) {
                byte[] buf = new byte[8192];
                int r;
                while ((r = in.read(buf)) > 0) {
                    bos.write(buf, 0, r);
                }
                return bos.toString("UTF-8");
            }
        } catch (Exception e) {
            return null;
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    private static void progress(Listener l, long done, long total, int partsDone, int partsTotal) {
        l.onProgress(done, total, String.format(Locale.US, "%d/%d parts done", partsDone, partsTotal));
    }
}