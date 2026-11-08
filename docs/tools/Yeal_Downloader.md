# Tool: Yeal Downloader

## Identity
Name: Yeal (video / audio downloader, brand "MediaOrbit" for the player). Target users: the owner and family on Windows 11 (Android planned). Status: development, version 0.9.1.38, no current exe. Area: the whole app except the TIDAL DIY and player parts ([TIDAL_DIY.md](TIDAL_DIY.md), [MediaOrbit_Player.md](MediaOrbit_Player.md)).

## Problem and benefit
Saves videos and music from YouTube and other sites (and TIDAL through tiddl) in tidy folders with tags, covers, lyrics and an HTML player page, without command-line work. Result: files + pages next to each other, history of finished downloads.

## Functions
- Core: download with profiles (F-01), audio choice (F-02), playlists (F-03), albums from tracklists (F-04), live recording (F-05), extras (F-06), HTML page (F-07), duplicate check (F-18).
- Secondary: frame extractor (F-13), external drives (F-14), yt-dlp update (F-15), vault/login pack (F-16), ad blocker (F-17, experimental), stream to box (F-12), embedded YouTube view.
- Not included: Seal code, speech-to-text (idea only), YouTube on Android until a JS runtime exists, downloading without a valid TIDAL subscription for TIDAL.

## Domain logic
See [03_DOMAIN_MODEL.md](../03_DOMAIN_MODEL.md): job states, gentle mode, MP3 = 320 kbps only, optional parts never fail a download, error texts in plain language, rate-limit pause 90 s.
Validation: `DownloadOptions.normalized`, `FORBIDDEN_KEYS`, `Settings.validate`.

## Inputs / outputs
In: links (field, drag and drop, browser view), profile/options, cookies (browser or `cookies.txt`), settings. Out: files in `Video\`, `Audio\`, `Playlists\`, album folders, HTML/TXT/LRC extras, `history.json`.
Persistence and formats: [04_DATA_MODEL.md](../04_DATA_MODEL.md).

## Architecture
Qt/QML pages -> `Backend` -> `DownloadQueue` -> `Engine` (yt-dlp) -> extras; helpers ffmpeg, Node. Details: [02_ARCHITECTURE.md](../02_ARCHITECTURE.md), interfaces [07_INTERFACES.md](../07_INTERFACES.md).

## Operation
Typical flow in [06_WORKFLOWS.md](../06_WORKFLOWS.md) W-01, W-02, W-08, W-09. Special cases: unreadable Chrome/Edge cookies -> use a cookie file; bot check -> queue pauses.

## Tests
`test_core`, `test_integration_local`, `test_history`, `test_updater`, `test_drives`, `test_lyrics`, `test_mp3tags`, `test_album_page`, `test_frames_preview`, `test_adblock`, `test_vault`, `test_loginpack`, `test_streaming` (2 known failures).
Commands in [14_TEST_STRATEGY.md](../14_TEST_STRATEGY.md). Limits: no real YouTube/live/playlist runs in CI; Windows real-app checks of 0.8.6-0.8.9 listed in TODO.md are open.

## History and next steps
History: [../../CHANGELOG.md](../../CHANGELOG.md). Known issues: [11_KNOWN_ISSUES.md](../11_KNOWN_ISSUES.md). Next steps: not approved yet ([12_PROJECT_STATE.md](../12_PROJECT_STATE.md)).
