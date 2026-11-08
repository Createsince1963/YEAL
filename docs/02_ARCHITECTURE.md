# 02 Architecture

The layer diagram and the TIDAL DIY diagram stay in [ARCHITECTURE.md](ARCHITECTURE.md) (kept as the detail source, not duplicated here; see
decision D-011 in [09_DECISIONS.md](09_DECISIONS.md)). This file adds the module map and the rules, and notes where the old file is out of date.

## Layers
```
QML (Main, pages, cards, Theme singleton)         context properties: backend, jobModel, tidal
  -> ui/backend.py      Backend(QObject), JobModel, JobFilterModel     (102 slots)
  -> ui/tidal_backend.py TidalBackend, TidalPlayer, QueueModel         (42 slots)
  -> ui/local_player.py LocalPlayer(TidalPlayer), LocalOwner           (player for downloaded files)
  -> ui/dsp_media.py, ui/crossfade.py, ui/calibration*.py, ui/perfmon.py
core/ (no Qt): queue, engine, presets, models, settings, history, tidal, tidal_api, streaming, extras, album, lyrics,
               mp3tags, vault, loginpack, updater, adblock, localserve, frames, dsp, audiodev, audioprobe, music_sources
platforms/ (PlatformInfo; desktop.py, android.py, drives.py)
```
Download path: `Backend.addUrls` -> `DownloadQueue.add` (4 daemon workers, `max_parallel` gate) -> `Engine.run` -> yt-dlp or the TIDAL branch
(`core/tidal.run_download`, tiddl subprocess) -> post steps (extras, album tags, MP3 convert, HTML pages). Worker threads hand job snapshots to
Qt queued signals (`_jobChanged`, `_jobRemoved`); they never touch QML objects.

## Rules (from ARCHITECTURE.md, CLAUDE.md, verified where noted)
1. `core/` imports no Qt and no platform code. Verified 2026-11-07: no `PySide6` import under `yeal/core`.
2. Per-OS differences live in `platforms/`; capability (e.g. `PlatformInfo.can_merge` = ffmpeg present) drives behaviour, not the OS name.
3. Worker threads never touch QML objects.
4. Python 3.11 compatible (Android wheels are cp311); desktop runs 3.13.
5. Only QtCore/QtGui/QtQml/QtQuick/QtQuickControls2 - no QtWidgets (verified: no `QtWidgets` in the source). **One deliberate exception:**
   `ui/tidal_backend.py` also uses QtMultimedia (own player), imported lazily.
6. `yt_dlp` is imported lazily after `updater.activate()`, never at module level.
7. `PlatformInfo.js_runtime` (Node) is passed to yt-dlp as `js_runtimes`; YouTube cannot be extracted without one.
8. Custom yt-dlp options are filtered by `FORBIDDEN_KEYS` (exec hooks, postprocessor chain, external downloaders, output paths, browser cookies).
9. QML property naming: no `on` + capital names; roles use `jobState`, not `state`.
10. Rows of buttons are `Flow`, never a plain `Row` wider than the card (OR-005).
11. Performance: no Canvas `shadowBlur`; canvases repaint at most ~20 Hz; long work in the GUI thread must be sliced (OR-006).

## Module map
| Module | Role | Doc |
|---|---|---|
| `core/models.py` | `DownloadOptions`, `DownloadJob`, `JobState` | [04](04_DATA_MODEL.md) |
| `core/settings.py` | `Settings` dataclass, validation, profiles | [04](04_DATA_MODEL.md) |
| `core/presets.py` | options -> yt-dlp dict, `FORBIDDEN_KEYS` | [05](05_FUNCTIONS.md) |
| `core/queue.py` | thread queue, cancel/retry/remove, rate-limit pause | [05](05_FUNCTIONS.md) |
| `core/engine.py` | runs one job, fallbacks, TIDAL branch, probes | [05](05_FUNCTIONS.md) |
| `core/tidal.py`, `core/tidal_api.py` | tiddl helper (downloads) / native TIDAL web API (browsing, playback) | [modules/tidal.md](modules/tidal.md) |
| `ui/tidal_backend.py` | TIDAL DIY backend + shared player base `TidalPlayer` | [modules/tidal.md](modules/tidal.md), [modules/players.md](modules/players.md) |
| `ui/local_player.py`, `core/music_sources.py` | player for downloaded files, music folders | [modules/players.md](modules/players.md) |
| `core/dsp.py`, `ui/dsp_media.py`, `ui/crossfade.py`, `ui/calibration*.py`, `core/audiodev.py` | own audio engine, crossfade, sound check | [modules/audio_engine.md](modules/audio_engine.md) |
| `core/vault.py`, `core/loginpack.py` | secrets | [modules/security_and_logins.md](modules/security_and_logins.md) |
| `core/updater.py` | yt-dlp self-update | [05](05_FUNCTIONS.md) |
| `core/streaming.py` | UPnP/DLNA "Stream to box" | [05](05_FUNCTIONS.md) |
| `core/extras.py`, `core/album.py`, `core/lyrics.py`, `core/mp3tags.py` | files next to a download | [05](05_FUNCTIONS.md) |
| `core/frames.py`, `core/adblock.py`, `core/localserve.py`, `core/audioprobe.py`, `core/history.py`, `platforms/drives.py` | support | [05](05_FUNCTIONS.md) |

## Deviations / outdated statements found in the old architecture file
- ARCHITECTURE.md says `Backend` + "Downloads / Profiles / Settings pages" only; the sun-view players, Folders/Speaker/Sound planets and the DSP engine
  (0.9.1.09-0.9.1.38) are described only in CHANGELOG.md and HANDOFF_TIDALGUI.md. This file and [modules/players.md](modules/players.md) now carry them.
- Rule 5 exception is also true for `ui/dsp_media.py` (QAudioSink) - assumed from the module's purpose; **not verified line by line**.

## Packaging
`Yeal.spec` (PyInstaller): packs QML, tiddl and its dependencies; ffmpeg must sit in `bin\` next to the exe (or `YEAL_EMBED_TOOLS=1`).
numpy is not in the exe -> the own audio engine falls back to Qt's player there. Last built exe: 0.9.1.06 (`dist\Yeal.exe`, old).
