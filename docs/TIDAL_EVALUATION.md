# Tidal integration: evaluation of candidate projects (2026-10-24)

Status: Yeal 0.8.14+ contains no Tidal code. All Tidal work starts with version 0.9.0.0.
Facts below come from the GitHub pages as fetched on 2026-10-24; commit dates were not visible and are unverified.

## Ranking (usefulness / fit for Yeal)

| # | Project | License | Fit | Verdict |
|---|---------|---------|-----|---------|
| 1 | oskvr37/tiddl | Apache-2.0 | Python CLI, `pip install tiddl`, quality LOW/NORMAL/HIGH/MAX (to 24-bit/192 kHz FLAC), ffmpeg, `config.toml`, device login via `tiddl auth login`, 691 stars, no archive notice | Best base: run as a subprocess from Yeal (same pattern as yt-dlp), parse its output for progress. No documented Python API, so do not import internals. |
| 2 | r3ferrei/tidal-dl-ng-1 (fork of exislow/tidal-dl-ng) | not stated on page | Python 3.12, PySide6 GUI, multithreaded, lyrics/cover/metadata, FLAC extraction | Best reference for a PySide6 GUI and metadata handling; check upstream exislow/tidal-dl-ng for maintenance before relying on the fork (83 stars). Possible fallback engine. |
| 3 | cstaelen/tidarr | license not shown | Docker, React + Express, uses tiddl 3.4.3, REST API with X-API-KEY, active, single maintainer | Reference for queue/sync/library ideas (Plex, Jellyfin, Lidarr). Not suited for embedding in a desktop app; optional "remote Tidarr server" mode only. |
| 4 | yaronzz/Tidal-Media-Downloader | Apache-2.0 | 4.3k stars, 405 open issues; recent issues: API keys broken (#1213, 2026-03-21), dash+xml stream (#1207), no FLAC (#1215), "APP Down" (#1204); issue #1216 asks to point to a maintained fork | Do not integrate. Mine the issues as a risk list (see below). |
| 5 | yaronzz/Tidal-Media-Downloader-PRO | Apache-2.0 | Windows GUI (tidal-gui), C#/Python, 1.4k stars | Do not integrate. Old GUI, same token problems, different language. |
| 6 | nicopowa/tidalext | GPL-3.0 | Browser extension (WebExtensions API), reads session cookies and intercepts fetch; 69 stars, 13 commits | Cannot run inside Qt WebEngine as-is, GPL-3.0 conflicts with copying code. Only the idea (cookie store + request interceptor) is reusable. Last choice. |

## Risks learned from the issue tracker
- Tidal rotates app tokens/API keys; any hard-coded key will break. Use a maintained engine and update it independently of Yeal.
- Stream manifest types change (dash+xml); FLAC is not always delivered (MAX vs MASTER naming, mp4a fallback).
- Rate limiting / account flags when many tracks are downloaded in parallel: keep concurrency low.
- A paid Tidal subscription is required. All projects state "private use only"; downloading may violate Tidal's terms of service and local copyright law. Yeal should show this notice and use only the user's own login.

## Proposed plan for Yeal 0.9.0.0
1. Bump VERSION to 0.9.0.0, new CHANGELOG section.
2. Engine adapter `yeal/engines/tidal.py` wrapping the tiddl CLI (detect/install via pip, version check, manual path like ffmpeg/Node.js).
3. Settings group "Tidal": login (device flow in the system browser), quality, target folder, concurrency (default low), legal notice shown once.
4. Reuse Yeal's tile list for albums/playlists, per-track and overall progress bars, relative-link HTML pages, MP3/FLAC tag step (default No).
5. Tests with a fake tiddl executable; no real account needed in CI.
