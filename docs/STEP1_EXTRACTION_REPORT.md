# LiveMCQ — Step 1 Extraction Report

**Date:** 06 October 2026
**Device:** Waydroid (Android 13, x86_64) on host `sakib`
**Package:** `com.livemcq.livemcq`
**Authorization:** LMCQ-DR-2026-1006 (Nabil Rahman → Sakib Khan)

---

## What was extracted

### 1. APK files (`extracted/`)

| File | Size | Notes |
|---|---|---|
| `base.apk` | 84.8 MB | Main APK — manifest, resources, Flutter assets |
| `split_config.x86_64.apk` | 81.9 MB | Native libs incl. `libapp.so` (Dart AOT), `libisar.so`, `libsqlcipher.so` |
| `split_config.en.apk` | 0 bytes | Pull failed (non-critical, locale config) |

Decompiled with:
- **JADX** → `extracted/apk_src/` (resources + Java sources; 366 decompile errors — normal for an APK this size)
- **Manual unzip** → `extracted/apk_base/`, `extracted/apk_x86/`

### 2. Local app data (`extracted/` — full `/data/data/com.livemcq.livemcq`)

| Item | Size | Value |
|---|---|---|
| `app_flutter/default.isar` | 1 MB | **Isar DB — local cache**: exams, answers, favorites, videos, audio questions |
| `app_flutter/GetStorage.gs` | 394 B | User ID `REDACTED`, install campaign, **video-token JWT** |
| `shared_prefs/FlutterSharedPreferences.xml` | ~50 KB | Full cached homepage JSON: user profile (uid REDACTED), notifications, config |
| `shared_prefs/FlutterSecureStorage.xml` | — | Encrypted (AndroidX Keystore) — **cannot decrypt off-device** |
| `databases/` | — | Only Google analytics DBs (no app SQLite) |
| `cache/` | — | Flutter image cache, Microsoft Clarity, crash reports |

**Isar schema recovered (7 collections):**
`AppSettings`, `IsarDataStoreModel`, `IsarReadFavModel`, `IsarExamModel` (exam answers JSON),
`IsarVideoModel`, `IsarAudioModel`, `SearchSuggestion`

### 3. App account on device
- app_user_id: `REDACTED`, user_id: `REDACTED`
- phone: `REDACTED` — **matches Nabil Rahman's number in the authorization letter**
- display_name: "REDACTED", email: REDACTED (appears to be a test/owner account)

---

## Infrastructure map (from `libapp.so` strings)

| Purpose | URL |
|---|---|
| **Main API** | `https://livemcq.com/api/v1/` |
| Operations panel | `https://operations.livemcq.com/` (analytics, payment-create, omr) |
| Game server | `https://game.livemcq.com/` |
| Web assets | `https://files.livemcq.app/` |
| BDIX file server | `https://bdix1.livemcq.com/audio-files` |
| Web frontend | `https://web.livemcq.com/` |
| Vocabulary embed | `https://vocabulary.livemcq.com/embed` |
| Firebase RTDB | `https://live-mcq.firebaseio.com` |
| Firebase API key | `AIzaSyCFEbDRyG2ENUfmxiUYvqf2xhFPZJ8Y0Po` |
| AWS S3 bucket | `elasticbeanstalk-ap-southeast-1-051040323559.s3...amazonaws.com/livemcq-files` |

**Sister apps found in binary:** Live Written (iOS id1645753246), Medical Higher Study (id6451155819), Live MCQ iOS (id1644524044), MS Store build.

**No `.env` file** — unlike the Softmax app, endpoints are compiled into the Dart AOT binary.

---

## Limitations (honest)

1. **Original Dart source code CANNOT be fully recovered from the APK.**
   Flutter AOT-compiles Dart into `libapp.so`. JADX only recovers the thin Java/Kotlin
   shell (plugins/engine). Recovering Dart-level logic requires snapshot reverse-engineering
   tools (blutter/direwolf) and yields partial, hard-to-read output — not a rebuildable project.
   → **The server-side repo (if it exists) or a rewrite is the realistic path to "source code".**
2. Encrypted secure-storage values are device-bound (Keystore) — unrecoverable off-device.
   Not needed: the API JWT was in GetStorage (plaintext).
3. `split_config.en.apk` pull failed — locale-only, not needed.

---

## What this unlocks — Step 2 (pending)

The main API is `https://livemcq.com/api/v1/`. Following the Softmax methodology:

1. Discover endpoint paths (Dart string analysis / probe with known JWT)
2. Authenticate — **existing device JWT may work**, otherwise OTP to `REDACTED`
   (the number is on the letter; OTP rate limits apply — 10 per 2 days)
3. Dump all content: exams, questions, videos, audio, books, users (as owned by Nabil)
4. Pull S3 bucket `livemcq-files` + BDIX audio files (needs AWS/hosting credentials)

**Blocked on brother (Nabil):** server/hosting credentials (cPanel/AWS/SSH) for
`livemcq.com` — required for server-side code + production database (the true source of truth).
