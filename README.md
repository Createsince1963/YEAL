# Yeal

Video and audio downloader built on [yt-dlp](https://github.com/yt-dlp/yt-dlp), with a Qt 6 / QML interface
written in Python (PySide6). One code base, two targets: **Windows 11 desktop** and **Android APK**
(via `pyside6-android-deploy`).

Yeal is inspired by [Seal](https://github.com/JunkFood02/Seal), the open-source Android video/audio downloader,
and its feature set. Yeal is an independent, from-scratch implementation:
**no Seal source code, name, icon or assets are used**.

Current version: see [`VERSION`](VERSION). Full history: [`CHANGELOG.md`](CHANGELOG.md).
How versions are kept safe: [`docs/VERSIONING.md`](docs/VERSIONING.md).

User manuals: [Deutsch](help/manual-de.html) · [English](help/manual-en.html) · [Help index](help/README.md)

## Features (v0.8.x)

### Downloading
- **Video or audio**, quality cap (360p ... 2160p / best), profile "Video 4K" included.
- **Audio**: MP3 is the default, always created at 320 kbps (never lower, otherwise no download). If the source is
  better than a typical stream, a dialog offers MP3 (recommended), AAC (M4A), the original stream, or FLAC for lossless sources.
- **Several links at once**, parallel downloads (1-4), cancel / retry / remove, duplicate check
  ("Download again?" or open the existing file).
- **Playlists**: a playlist link opens a list of all entries; tick single entries, a Shift+click range, or everything
  (Ctrl+A). Saved in `Playlists\<name>\`, numbered like the playlist, plus a `<name>.html` playlist page with one player
  and the entry list.
- **Live streams**: a running live stream is detected; Yeal asks whether to record it and for how long
  (until it ends, 15 / 30 min, 1 / 2 h, or custom minutes; needs ffmpeg).
- **Albums from tracklists**: if the description contains timestamps, Yeal offers *Tracks only*, *Tracks + full file* or *No thanks*.
  Tracks get song names, tags (album, artist, track n/N) and an `.m3u8` playlist; chapters are embedded as markers.
- **Gentle mode** (on by default): pauses between requests, 3-8 s between playlist items, back-off after errors; a rate limit
  or bot check pauses the whole queue for 90 s.
- Optional **browser login cookies** (Firefox / Edge / Chrome) for age-restricted, members-only and Premium videos.
- Optional parts never fail a download: missing subtitles, cover or quality are skipped with a hint on the tile.
- Plain-language error explanations (rate limit, private / age-restricted / members video, country block, removed video,
  no connection, ffmpeg, disk, YouTube change) with the technical line still available.

### Extras saved next to the download
- **MP3 tags** filled automatically from the video description (genre, mood, ...), plus a short "edit MP3 tags?" prompt (default No).
- **Lyrics**: looked up online (LRCLIB, no key) or taken from captions; saved as TXT and timed LRC, written into MP3/M4A tags
  (SRT for video) and shown highlighted and clickable in the HTML page.
- **Description (HTML, clickable links) and transcript (TXT)**, named like the video.
- **HTML page with player**: local file player plus optional online player (YouTube / Vimeo); timestamps of tracklists jump in the player.
  "Open page" can open the independent local file directly (default), or optionally serve it on 127.0.0.1 so the embedded online player works.
- Cover image and metadata embedded (needs ffmpeg).

### Image extractor (desktop, needs ffmpeg)
Split a video into images: video tiles (also drag in from Explorer), film strip with a selection frame, preview player,
interval 0.1 / 0.5 / 1 ... 60 s (below 1 s only for Shorts), JPG or PNG, one folder per video under `Frames\`.

### Embedded YouTube browser (Windows)
- The Microsoft Edge WebView2 of Windows 11 is used; no browser is bundled. Sign-in is kept in the Yeal data folder.
- Back / Forward (also Alt+Left / Alt+Right) / Reload (F5) / start page. Back and Forward keep their own page history, so they
  still work after a dialog re-created the view.
- Opening a video, Short or playlist fills the link field with a cleaned link (video id only); nothing downloads until you press Download.
- Follows the app theme (dark / light); the sound is muted during ads and restored afterwards.
- Experimental ad blocking (off by default): local filter proxy plus a script that hides ad slots and skips ads.
- Show / hide the browser, swap the sides and drag the divider; width and side are remembered.

### Workflow, files and drives
- **Profiles**: named presets (format, quality, audio format, subtitles, playlists, metadata, album mode, lyrics, ...).
- Download list grouped by date (Today, Yesterday, weekday, week, year), collapsible, filter tabs, search; the last 500
  finished downloads are remembered.
- **External drives**: a newly connected USB / external drive is offered as download target (folder name editable); dropdown with
  the Windows Downloads folder on top and each drive with free / total space.
- Downloads are sorted into `Video\` and `Audio\` sub-folders; right-click menus, drag & drop of links, "Show in folder",
  "Play in VLC (fullscreen)" when VLC is installed.
- Download folder chosen with the system folder dialog.

### Settings, security, updates
- Theme (light / dark / system), parallel downloads, speed limit, proxy, custom yt-dlp options as JSON (a safe subset: no exec
  hooks, no external downloaders).
- **yt-dlp self-update** from PyPI (sha256 checked, checked every 3 days, button in Settings).
- **Admin vault**: stored logins locked with an admin password, encrypted with Windows DPAPI plus a password-derived key;
  auto-lock after 5 minutes, clipboard cleared after 30 s. "Delete all logins" also wipes the browser sign-in.
- Layout adapts to the window width (sidebar or bottom bar); window size and position are remembered.
- Shortcuts: Ctrl+1 / 2 / 3 switch pages, Ctrl+L focuses the link field.

## Quick start (Windows, central Python from Tools_Central)

```
Run_Yeal.bat           start the app
Test_Yeal.bat          run all tests
Build_Yeal_Exe.bat     PyInstaller build -> dist\Yeal.exe (ffmpeg + node copied to dist\bin)
Build_Yeal_Exe.bat slim    same, without Qt's bundled FFmpeg (about 8 MB smaller, see CHANGELOG 0.8.11)
Build_Yeal_Exe.bat embed   ffmpeg + node packed inside the exe (about 100 MB bigger)
```

ffmpeg is found via `YEAL_FFMPEG`, `bin\ffmpeg.exe`, `Tools_Central\Video Tools\FFMPEG\bin`, then `PATH`.
YouTube also needs a JavaScript runtime (Node 22+ or Deno): `YEAL_NODE`, `bin\node.exe`,
`Tools_Central\Dependencies\node\bin\node.exe`, then `PATH`.
Optional variables: `YEAL_DATA_DIR`, `YEAL_DOWNLOAD_DIR`. An empty `portable.flag` next to the app keeps settings in `.\data`.
Debug starts: `Run_Yeal_Debug.bat`, `Run_Yeal_Debug_Fresh.bat`, `Run_Yeal_NoGPU.bat`.

## Project layout

```
BIN/versions/v0.1/PyModul/      the app (this folder is what gets deployed)
  main.py                       entry point (name is required by pyside6-android-deploy)
  yeal/core/                    models, presets, settings, engine, queue, updater, history, vault, lyrics, mp3tags, ... (no Qt)
  yeal/platforms/               PlatformInfo + desktop.py / android.py / drives.py
  yeal/ui/backend.py            Qt bridge (JobModel, Backend)
  yeal/ui/qml/                  design system (Theme, Icon, controls) + pages and dialogs
tests/                          test suites (core, QML smoke, local end-to-end)
docs/                           ARCHITECTURE.md, ANDROID.md, VERSIONING.md
help/                           German and English HTML user manuals
ci/build-apk.yml                cloud APK build
```

## Legal note

yt-dlp is public domain (Unlicense). Download only content you are allowed to download.
If you ever copy code from Seal (GPL-3.0), Yeal becomes GPL-3.0 too and must not use the Seal name.
