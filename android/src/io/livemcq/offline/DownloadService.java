package io.livemcq.offline;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;

import java.util.Locale;

/**
 * Foreground service that owns the content download so it keeps running when
 * the app is backgrounded or the screen is off. Relays live progress to the
 * activity via {@link #setListener(Listener)} if one is attached.
 */
public final class DownloadService extends Service implements ContentManager.Listener {

    private static final String CHANNEL_ID = "livemcq_download";
    private static final int NOTIFICATION_ID = 1;

    private static volatile Listener uiListener;
    private static volatile boolean running;
    private static volatile long lastDone;
    private static volatile long lastTotal;
    private static volatile String lastDetail = "";

    private NotificationManager nm;
    private PowerManager.WakeLock wakeLock;
    private ContentManager cm;
    private boolean finished;

    public interface Listener {
        void onProgress(long doneBytes, long totalBytes, String detail);
        void onError(String message);
        void onDone();
    }

    public static void setListener(Listener l) {
        uiListener = l;
        if (l != null && running) {
            l.onProgress(lastDone, lastTotal, lastDetail);
        }
    }

    public static boolean isRunning() {
        return running;
    }

    public static void cancel() {
        if (lastCm != null) {
            lastCm.cancel();
        }
    }

    private static volatile ContentManager lastCm;

    @Override
    public void onCreate() {
        super.onCreate();
        nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel ch = new NotificationChannel(
                    CHANNEL_ID, "LiveMCQ download", NotificationManager.IMPORTANCE_LOW);
            ch.setDescription("Shows progress while the content bundle downloads.");
            nm.createNotificationChannel(ch);
        }
        PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "livemcq:download");
        wakeLock.acquire(8 * 60 * 60 * 1000L);
        cm = new ContentManager(this);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (running) {
            return START_NOT_STICKY;
        }
        String url = intent != null ? intent.getStringExtra("url") : null;
        if (url == null || url.trim().isEmpty()) {
            url = cm.savedUrl();
        }
        if (url == null || url.trim().isEmpty() || cm.isReady()) {
            stopSelf();
            return START_NOT_STICKY;
        }
        running = true;
        lastCm = cm;
        startForeground(NOTIFICATION_ID, notif(0, 1, "Connecting…"));
        cm.sync(url.trim(), this);
        return START_STICKY;
    }

    @Override
    public void onProgress(long doneBytes, long totalBytes, String detail) {
        lastDone = doneBytes;
        lastTotal = totalBytes;
        lastDetail = detail;
        nm.notify(NOTIFICATION_ID, notif(doneBytes, Math.max(1, totalBytes), detail));
        Listener l = uiListener;
        if (l != null) {
            l.onProgress(doneBytes, totalBytes, detail);
        }
    }

    @Override
    public void onError(String message) {
        running = false;
        finished = true;
        nm.notify(NOTIFICATION_ID, doneNotif("Failed: " + message, false));
        Listener l = uiListener;
        if (l != null) {
            l.onError(message);
        }
        stopSelf();
    }

    @Override
    public void onDone() {
        running = false;
        finished = true;
        nm.notify(NOTIFICATION_ID, doneNotif("Download complete — open LiveMCQ", true));
        Listener l = uiListener;
        if (l != null) {
            l.onDone();
        }
        stopSelf();
    }

    private Notification notif(long done, long total, String detail) {
        Notification.Builder b = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);
        Intent i = new Intent(this, MainActivity.class);
        PendingIntent pi = PendingIntent.getActivity(this, 0, i,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        boolean determinate = total > 1;
        int pct = determinate ? (int) Math.min(100, done * 100L / total) : 0;
        String text = determinate
                ? String.format(Locale.US, "%d%% · %.2f / %.2f GB", pct, done / 1073741824.0, total / 1073741824.0)
                : "Starting…";
        b.setSmallIcon(android.R.drawable.stat_sys_download)
                .setContentTitle("LiveMCQ — downloading content")
                .setContentText(text)
                .setOnlyAlertOnce(true)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setContentIntent(pi)
                .setProgress(100, determinate ? Math.min(100, pct) : 0, !determinate)
                .setSubText(detail);
        return b.build();
    }

    private Notification doneNotif(String text, boolean sticky) {
        Notification.Builder b = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);
        Intent i = new Intent(this, MainActivity.class);
        PendingIntent pi = PendingIntent.getActivity(this, 0, i,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        b.setSmallIcon(android.R.drawable.stat_sys_download)
                .setContentTitle("LiveMCQ Offline")
                .setContentText(text)
                .setAutoCancel(!sticky)
                .setOnlyAlertOnce(true)
                .setContentIntent(pi);
        return b.build();
    }

    @Override
    public void onDestroy() {
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
        }
        if (!finished) {
            if (Build.VERSION.SDK_INT >= 24) {
                nm.cancel(NOTIFICATION_ID);
            }
        }
        running = false;
        super.onDestroy();
    }

    public static void start(Context ctx, String url) {
        Intent i = new Intent(ctx, DownloadService.class);
        i.putExtra("url", url);
        if (Build.VERSION.SDK_INT >= 26) {
            ctx.startForegroundService(i);
        } else {
            ctx.startService(i);
        }
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}