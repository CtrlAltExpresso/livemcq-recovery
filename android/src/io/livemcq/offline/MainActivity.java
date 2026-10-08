package io.livemcq.offline;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.ScrollView;

import java.io.File;
import java.io.IOException;
import java.util.Locale;

public class MainActivity extends Activity implements ContentManager.Listener {

    private ContentManager cm;
    private AssetServer server;
    private WebView web;

    private EditText urlField;
    private TextView tvStatus;
    private TextView tvProgress;
    private ProgressBar progressBar;
    private View startButton;
    private View cancelButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        cm = new ContentManager(this);

        if (cm.isReady()) {
            openViewer();
            return;
        }
        buildSetupUi();
    }

    // ---------------------------------------------------------------- setup

    private void buildSetupUi() {
        FrameLayout frame = new FrameLayout(this);
        frame.setBackgroundColor(Color.WHITE);

        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(24), dp(40), dp(24), dp(24));
        box.setBackgroundColor(Color.WHITE);

        TextView title = new TextView(this);
        title.setText("LiveMCQ Offline");
        title.setTextSize(24);
        title.setTypeface(null, Typeface.BOLD);
        title.setTextColor(Color.parseColor("#1a237e"));
        box.addView(title);

        TextView sub = new TextView(this);
        sub.setText("One-time download of the full content (~9 GB).\nAfter it finishes, the app works fully offline — no internet needed.");
        sub.setTextSize(14);
        sub.setTextColor(Color.parseColor("#444444"));
        sub.setPadding(0, dp(6), 0, dp(18));
        box.addView(sub);

        TextView lbl = new TextView(this);
        lbl.setText("Content URL (livemcq_manifest.json)");
        lbl.setTextSize(13);
        lbl.setTextColor(Color.parseColor("#666666"));
        box.addView(lbl);

        urlField = new EditText(this);
        urlField.setSingleLine(true);
        urlField.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        urlField.setText(cm.savedUrl().isEmpty() ? Config.DEFAULT_MANIFEST_URL : cm.savedUrl());
        urlField.setTextSize(14);
        urlField.setPadding(dp(8), dp(6), dp(8), dp(6));
        box.addView(urlField);

        tvStatus = new TextView(this);
        tvStatus.setText("Requires ~" + String.format(Locale.US, "%.1f GB free storage.", 9.5));
        tvStatus.setTextSize(12);
        tvStatus.setTextColor(Color.parseColor("#888888"));
        tvStatus.setPadding(0, dp(4), 0, dp(12));
        box.addView(tvStatus);

        startButton = newButton("Start download", "#1a237e");
        startButton.setOnClickListener(v -> startSync());
        box.addView(startButton);

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(1000);
        progressBar.setVisibility(View.GONE);
        progressBar.setPadding(0, dp(16), 0, 0);
        box.addView(progressBar);

        tvProgress = new TextView(this);
        tvProgress.setTextSize(12);
        tvProgress.setTextColor(Color.parseColor("#222222"));
        tvProgress.setPadding(0, dp(6), 0, 0);
        tvProgress.setVisibility(View.GONE);
        box.addView(tvProgress);

        cancelButton = newButton("Cancel", "#c62828");
        cancelButton.setVisibility(View.GONE);
        cancelButton.setOnClickListener(v -> cm.cancel());
        box.addView(cancelButton);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(box);
        frame.addView(scroll);
        setContentView(frame);
    }

    private View newButton(String text, String color) {
        TextView b = new TextView(this);
        b.setText(text);
        b.setTextSize(16);
        b.setGravity(Gravity.CENTER);
        b.setPadding(dp(12), dp(12), dp(12), dp(12));
        b.setBackgroundColor(Color.parseColor(color));
        b.setTextColor(Color.WHITE);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        lp.topMargin = dp(10);
        b.setLayoutParams(lp);
        return b;
    }

    private void startSync() {
        String url = urlField.getText().toString().trim();
        if (url.isEmpty()) {
            tvStatus.setText("Please paste the manifest URL first.");
            tvStatus.setTextColor(Color.parseColor("#c62828"));
            return;
        }
        urlField.setEnabled(false);
        startButton.setVisibility(View.GONE);
        progressBar.setVisibility(View.VISIBLE);
        tvProgress.setVisibility(View.VISIBLE);
        cancelButton.setVisibility(View.VISIBLE);
        tvStatus.setText("Contacting " + url);

        cm.sync(url, this);
    }

    @Override
    public void onProgress(final long doneBytes, final long totalBytes, final String detail) {
        runOnUiThread(() -> {
            if (totalBytes > 0) {
                progressBar.setProgress((int) Math.min(999, doneBytes * 1000 / totalBytes));
                tvProgress.setText(String.format(Locale.US, "%.2f / %.2f GB   %s",
                        doneBytes / 1073741824.0, totalBytes / 1073741824.0, detail));
            } else {
                tvProgress.setText(detail);
            }
        });
    }

    @Override
    public void onError(final String message) {
        runOnUiThread(() -> {
            tvStatus.setText(message);
            tvStatus.setTextColor(Color.parseColor("#c62828"));
            startButton.setVisibility(View.VISIBLE);
            urlField.setEnabled(true);
            cancelButton.setVisibility(View.GONE);
        });
    }

    @Override
    public void onDone() {
        runOnUiThread(() -> {
            tvStatus.setText("Done. Opening viewer…");
            openViewer();
        });
    }

    // ---------------------------------------------------------------- viewer

    private void openViewer() {
        File root = cm.contentRoot();
        try {
            server = AssetServer.start(root);
        } catch (IOException e) {
            if (web != null) {
                web.destroy();
            }
            finish();
            return;
        }

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setCacheMode(WebSettings.LOAD_NO_CACHE);
        web.setWebViewClient(new WebViewClient());
        web.setWebChromeClient(new WebChromeClient());
        web.setKeepScreenOn(true);
        web.loadUrl("http://127.0.0.1:" + server.port() + "/viewer/index.html");
        setContentView(web);
    }

    @Override
    protected void onDestroy() {
        if (server != null) {
            server.stop();
        }
        if (web != null) {
            web.destroy();
        }
        super.onDestroy();
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }

    private int dp(int n) {
        return Math.round(n * getResources().getDisplayMetrics().density);
    }
}