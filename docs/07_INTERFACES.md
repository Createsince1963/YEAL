# 07 Interfaces

## External programs and services
| Interface | Use | Notes / source |
|---|---|---|
| yt-dlp (+ yt-dlp-ejs) | all non-TIDAL downloads; imported lazily after `updater.activate()` | self-updated from PyPI; needs a JS runtime for YouTube |
| ffmpeg | merge, convert, frames, own audio engine decoding | lookup order: setting `ffmpeg_path`, `YEAL_FFMPEG`, `bin\ffmpeg.exe`, `Tools_Central\Video Tools\FFMPEG\bin`, PATH |
| Node 22+ / Deno | JS runtime for YouTube extraction | `YEAL_NODE`, `bin\node.exe`, `Tools_Central\Dependencies\node\bin\node.exe`, PATH |
| tiddl (Apache-2.0) | TIDAL downloads, `auth refresh`, login | subprocess only, never imported; embedded as `Yeal.exe --tiddl ...` in the exe |
| TIDAL web API | browsing, lyrics, playlist edits, stream URLs for the own player | unofficial; token from tiddl; endpoints checked 2026-10-25 (`v1/pages/*`, `v1/search`, `v1/tracks/{id}/playbackinfopostpaywall`, `v2/feed/activities?userId=` without trailing slash) |
| LRCLIB (`lrclib.net`) | lyrics lookup | no key; https only, size cap |
| PyPI | yt-dlp wheels | sha256 verified |
| UPnP/DLNA renderers | stream to box (KEF LS50 / LSX, TVs, Sonos, receivers) | SSDP + SOAP |
| Microsoft Edge WebView2 | embedded YouTube / TIDAL Web (Windows) | not bundled; QtWebView |
| Windows DPAPI | vault encryption | `core/vault.py` (ctypes) |
| VLC (optional) | "Play in VLC (fullscreen)" | if installed |
| mutagen (optional) | MP3 tags | downloads work without it |
| numpy (optional) | own audio engine | not in the exe |
| psutil (optional) | `YEAL_PERF` | optional |
| GitHub `Createsince1963/YEAL` | remote; Actions workflow for the APK in `ci\build-apk.yml` (not active) | push only on owner order |

## Internal interfaces
- QML context properties: `backend` (`ui/backend.py`, 102 slots), `jobModel`, `tidal` (`ui/tidal_backend.py`, 42 slots; local player 9 slots).
  QML never talks to the TIDAL API or to files directly.
- Signals worth knowing: `Backend.tidalDiyPlaying` (pause web players with `single_playback`), `TidalHome.videoLink(url)`, `Backend._jobChanged/_jobRemoved`.
- `PlatformInfo` (`platforms/__init__.py`): paths, ffmpeg, node, `can_merge`, `is_mobile`, `js_runtime`.
- `TidalHome` controller `ctl` API used by pages: `open, playItem, itemMenu, openList, search, addToPlaylist, download, askName, confirm, back, openInWeb, fmt, fmtLong, tileSize, setTileSize,
  currentId, pausePlayback` (from HANDOFF_TIDALGUI step 1; later changes not re-verified).
- Command line: `main.py --tiddl ...`, `main.py --calibrate [--json] [--list|--device|--stress|--minutes N|--apply]`.

## Files exchanged with the user
`*.yealpack` (login pack), `cookies.txt` (Netscape format, needs youtube.com/google.com cookies), `blocklist.txt`, `.m3u8`/M3U, HTML pages, LRC/TXT, `.yealpack` password never stored.

## Security of interfaces
Network answers are untrusted (LRCLIB, API); the media server for boxes serves only registered files to private networks; the local page server serves only its folder; no secrets in logs or URLs
(see [../SECURITY.md](../SECURITY.md) for the checklist template).
