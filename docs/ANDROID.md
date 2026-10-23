# Yeal on Android

Build path: `pyside6-android-deploy` (python-for-android + buildozer). It needs a **Linux host**,
so the build runs on a GitHub Actions runner, as for the other PySide6 apps in Tools_Central
(see `Tools_Central\pyside6-android-deploy\README.md` and its `TROUBLESHOOTING.md`).

## Build (only on explicit request)

1. Create a GitHub repo for Yeal, run `Tools_Central\pyside6-android-deploy\Setup-CloudBuild.ps1`
   (or push this folder yourself). The project has its own workflow in `ci/build-apk.yml`: copy it to `.github/workflows/build-apk.yml` in the repo (the central `Setup-CloudBuild.ps1` would install the Vacation-Finder template instead, so skip its workflow step or overwrite afterwards).
2. Trigger "Build Yeal APK" (`Build-Apk-Cloud.ps1` or the Actions tab) and download the `yeal-apk` artifact.
3. Record every failure and fix in the central `TROUBLESHOOTING.md`.

Debug-signed test builds only; a release needs its own keystore (`New-ReleaseKeystore.ps1`).

## Known gaps in v0.1 (honest list)

| Topic | Situation | Plan |
|---|---|---|
| ffmpeg | Not shipped. Video = single-file progressive stream, audio keeps native container. | Ship ffmpeg as a native lib (Android forbids running downloaded binaries) or use a prebuilt `libffmpeg` package. Prototype first. |
| yt-dlp bundling | Pure Python, expected to be picked up from `requirements.txt` / imports. **Unverified.** | Check the first APK; add it explicitly to `pysidedeploy.spec` if missing. |
| Permissions | `INTERNET` must be in the manifest. **Unverified.** | Check after first build; add through the spec / manifest template. |
| Download folder | `QStandardPaths.DownloadLocation` + `/Yeal` (scoped storage may redirect it to the app dir). | Verify on device; then MediaStore for public Downloads. |
| Share-to-Yeal | Not implemented. Use the Paste button. | Java/Manifest intent filter. |
| Background downloads | No foreground service: downloads can stop when the app is in background. | Foreground service via pyjnius/Qt Android classes. |
| Updating yt-dlp | The in-app updater (PyPI wheels into the app data dir) is shared code and should work as is. **Unverified on device.** | Test on first APK. |
| YouTube | Needs a JS runtime (Node/Deno/QuickJS) for yt-dlp-ejs; none exists on Android in v0.1, so YouTube will fail there. Other sites work. | Ship QuickJS as a native lib (yt-dlp supports `quickjs`) - Seal solves this natively. |
| Download folder chooser | Hidden on Android (the system dialog returns `content://` URIs, not paths). | SAF/MediaStore support. |
| QML files on device | Loaded from the file system next to `main.py`. | Confirm the deploy tool packages `*.qml` (listed in `pyproject.toml`). |

## First on-device checklist

1. App starts, UI is usable at phone width.
2. Direct mp4 link downloads and lands in the reported folder.
3. A YouTube link works (extractors depend on the bundled yt-dlp version).
4. Behaviour with screen off / app in background.
