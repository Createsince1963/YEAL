# 01 System overview

Facts verified against the working tree on 2026-11-07 (version file `VERSION` = 0.9.1.38). Not run: the test suites (see [14_TEST_STRATEGY.md](14_TEST_STRATEGY.md)).

## Locations
| What | Path |
|---|---|
| Project root (git, branch `main`, remote GitHub `Createsince1963/YEAL`) | `C:\Users\mail\AI_Coworker_Claude\APK YEAL` |
| App source (deployed folder) | `BIN\versions\v0.1\PyModul` (`main.py`, `yeal\core`, `yeal\platforms`, `yeal\ui`, `yeal\ui\qml`) |
| Tests | `tests\` (30 files `test_*.py`, 2 benchmark scripts) |
| Python (portable, central) | `C:\Users\mail\AI_Coworker_Claude\Tools_Central\Python\python\python.exe` (found by `_find_python.bat`) |
| User manuals (DE / EN) | `help\manual-de.html`, `help\manual-en.html` |
| Snapshots of versions | `_snapshots\<date>_v<version>_<reason>\` |
| Brand sources and logo scripts | `docs\brand\` |
| APK cloud build workflow (not active) | `ci\build-apk.yml`, `apk-project.json`, `apk_built.bat` |
| Old backups, to be deleted by the owner | `_to_delete\` |

## Size (lines, source only)
About 23,600 lines Python + QML under `PyModul`: `ui/backend.py` 2133, `ui/tidal_backend.py` 1248, `core/engine.py` 686, `core/tidal_api.py` 660,
`core/streaming.py` 546, QML largest `SettingsPage.qml` 879. 30 test files (about 440 test methods by static count).

## Entry points (batch files in the root)
| File | Purpose |
|---|---|
| `Run_Yeal.bat` | start the app |
| `Run_Yeal_NoGPU.bat`, `Run_Yeal_Debug.bat`, `Run_Yeal_Debug_Fresh.bat` | software rendering / debug / fresh data folder |
| `Test_Yeal.bat` | `unittest discover` (see known problem in [11_KNOWN_ISSUES.md](11_KNOWN_ISSUES.md) KI-001) |
| `Calibrate_Yeal.bat` | audio calibration ([modules/audio_engine.md](modules/audio_engine.md)) |
| `Build_Yeal_Exe.bat` (`slim`, `embed`) | PyInstaller build to `dist\Yeal.exe` - **only on the owner's request** |
| `Push_Tags.bat` | push tags - **only on the owner's request** |
| `exe_built.bat`, `apk_built.bat` | build entry points ("built" scripts); content not analysed in this initialisation |

## Command line and environment
- `main.py --tiddl ...` runs the embedded tiddl; `main.py --calibrate [--json] ...` runs the sound calibration (`Yeal.exe --tiddl/--calibrate` in the exe).
- Environment: `YEAL_DATA_DIR` (data folder), `YEAL_DOWNLOAD_DIR`, `YEAL_FFMPEG`, `YEAL_NODE`, `YEAL_PERF=1` (CPU/RAM/GUI-lag print every 2 s),
  `YEAL_LOG=1` (log file also when not frozen), `YEAL_EMBED_TOOLS=1` (build with ffmpeg + node inside), `portable.flag` next to the app (data in `.\data`).
- Tests: `QT_QPA_PLATFORM=offscreen`, `QT_QUICK_BACKEND=software`.

## Main building blocks (details in [02_ARCHITECTURE.md](02_ARCHITECTURE.md))
1. Download pipeline: QML pages -> `Backend` -> `DownloadQueue` -> `Engine` (yt-dlp / tiddl) -> files + extras.
2. Embedded browser views (Windows WebView2): YouTube and TIDAL Web (`WebPane.qml`, `TidalPane.qml`).
3. TIDAL DIY: native TIDAL browser and player (`core/tidal_api.py`, `ui/tidal_backend.py`, `Tidal*.qml`).
4. Player for downloaded files (`ui/local_player.py`, `LocalPlayerView.qml`) and the shared sun view (`SunView.qml`).
5. Own audio engine (`core/dsp.py`, `ui/dsp_media.py`) with calibration (`ui/calibration*.py`).
6. Support: settings/profiles, history, vault, login pack, updater, streaming to UPnP boxes, frame extractor, ad blocker.

## Data folder (user data)
Location chosen by `platforms` (desktop), overridable by `YEAL_DATA_DIR` or `portable.flag`. Contents known from code:
`settings.json`, `history.json` (newest 500 finished jobs), `vault.json`, `ytdlp\` (self-updated yt-dlp + `stamp.json`), `tiddl\` (own tiddl home with
`config.toml` and mirrored `auth.json`), `youtube_cookies.txt`, `audio_profile.json`, `audio_report.json`, `blocklist.txt` (optional), `yeal.log` / `yeal.prev.log`.
See [04_DATA_MODEL.md](04_DATA_MODEL.md).
