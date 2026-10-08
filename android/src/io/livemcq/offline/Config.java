package io.livemcq.offline;

/**
 * Build-time configuration. The build script regenerates this with a baked-in
 * URL when SOURCE_URL is set; the committed copy is only a fallback used when
 * nothing was baked in (the user can also paste a URL in the app's setup UI).
 */
public final class Config {
    public static final String DEFAULT_MANIFEST_URL = "";
}