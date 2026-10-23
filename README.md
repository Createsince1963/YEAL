# Yeal

Workspace: `C:\Users\mail\AI_Coworker_Claude\APK YEAL\` (toolchains stay in `..\Tools_Central`).

Video/audio downloader built on [yt-dlp](https://github.com/yt-dlp/yt-dlp) with a Qt 6 / QML
interface in Python (PySide6). One code base, two targets: **Windows 11 desktop** and
**Android APK** (via `pyside6-android-deploy`).

Inspired by the feature set of the Android app Seal. Yeal is an independent, from-scratch
implementation: **no Seal source code, name, icon or assets are used**.

## Status (v0.1.0)

| Area | State |
|---|---|
| Engine, queue, settings, presets | done, unit tested (real yt-dlp + ffmpeg, local server) |
| QML UI (desktop and phone layout) | done, loads without warnings, rendered and checked offscreen |
| Windows run / `.exe` build scripts | written; run on your PC to confirm (see Quick start) |
| Android APK | **not built yet** - workflow exists, first cloud run still pending |
| yt-dlp self-update from PyPI | done, tested against real PyPI |
| Real internet downloads (YouTube etc.) | not tested in the dev sandbox (no internet there); first real check is yours |

## Quick start (Windows, central Python from Tools_Central)

```
Run_Yeal.bat           start the app
Test_Yeal.bat          run all tests
Build_Yeal_Exe.bat     PyInstaller build -> dist\Yeal\Yeal.exe (bundles ffmpeg from Video Tools)
```

The scripts use `Tools_Central\Python\python\python.exe` (PySide6 6.11, yt-dlp, PyInstaller are
already installed there) and never modify it. ffmpeg is found automatically:
`YEAL_FFMPEG` env var, `bin\ffmpeg.exe` next to the app, `Tools_Central\Video Tools\FFMPEG\bin`, then `PATH`.

YouTube also needs a JavaScript runtime (Node 22+ or Deno). Node is found automatically:
`YEAL_NODE`, `bin\node.exe` next to the app, `Tools_Central\Dependencies\node\bin\node.exe`, then `PATH`.

**yt-dlp updates:** Yeal downloads the newest yt-dlp (and its `yt-dlp-ejs` solver) into its data folder
(`%APPDATA%\Yeal\ytdlp`) and uses that instead of the Python installation's copy. If YouTube links
fail with errors like "The page needs to be reloaded", press Settings -> Update yt-dlp and restart Yeal.

Optional environment variables: `YEAL_DATA_DIR`, `YEAL_DOWNLOAD_DIR`, `YEAL_FFMPEG`, `YEAL_NODE`. Create an empty
`portable.flag` next to the app to keep settings in `.\data`.

## Features

- Video or audio, quality cap (360p ... 2160p / best), audio as m4a / mp3 / opus / original
- Several links at once (one per line), playlists, parallel downloads (1-4), cancel / retry
- Subtitles, embedded metadata + thumbnail (needs ffmpeg)
- Advanced yt-dlp options as JSON (a safe subset: no exec hooks, no external downloaders)
- Right-click menus (long-press on touch) on downloads, the link field and the list
- Download folder chosen with the system folder dialog
- Keeps yt-dlp current itself (Settings -> Update yt-dlp, plus a check every 3 days)
- Layout adapts to window width (desktop vs. phone)

## Project layout

```
BIN/versions/v0.1/PyModul/      the app (this folder is what gets deployed)
  main.py                       entry point (name is required by pyside6-android-deploy)
  yeal/core/                    models, presets, settings, engine (yt-dlp), queue, updater - no Qt
  yeal/platforms/               PlatformInfo + desktop.py / android.py
  yeal/ui/backend.py            Qt bridge (JobModel, Backend)
  yeal/ui/qml/                  design system (Theme, Icon, controls) + pages (Downloads, Profiles, Settings)
tests/                          unittest suites (core, QML smoke, local end-to-end)
docs/                           ARCHITECTURE.md, ANDROID.md
ci/build-apk.yml                cloud APK build (copy to .github/workflows/ in the repo)
```

Central conventions followed: toolchains referenced from `Tools_Central`, never copied;
APK builds only on explicit request (`APK_BUILD_STANDARD.md`); security notes in `SECURITY.md`.

## Legal note

yt-dlp is public domain (Unlicense). Download only content you are allowed to download.
If you ever copy code from Seal (GPL-3.0), Yeal becomes GPL-3.0 too and must not use the Seal name.
