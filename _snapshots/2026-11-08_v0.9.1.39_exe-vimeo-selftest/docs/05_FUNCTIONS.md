# 05 Functions

Business-relevant functions in the protocol format (condensed: fields that are empty are left out). Helpers without own business logic are not listed.
Tests refer to files in `tests\` ([14_TEST_STRATEGY.md](14_TEST_STRATEGY.md)). Source modules are under `BIN\versions\v0.1\PyModul\yeal\`.

## F-01 Download a link (video / audio)
- Purpose: save media from a URL with the active profile. Trigger: Download button / link field / drag and drop of a link (`Backend.addUrls`).
- Inputs: URL(s), `DownloadOptions`. Outputs: file(s) in `Video\`/`Audio\`, extras, a finished job in the history.
- Flow: duplicate check -> `DownloadQueue.add` -> worker -> `Engine.run` (yt-dlp, `build_ydl_opts(options, PlatformInfo)`) -> progress/postprocessor hooks -> states.
  Fallbacks: `engine.apply_fallback` retries with changed options; unreadable browser cookies are dropped with a note (`COOKIE_NOTE_PREFIX`).
- Validation: `normalized()`; custom options via `FORBIDDEN_KEYS`. Errors: plain-language explanation + technical line (rate limit, private/age/member video, country block,
  removed, no connection, ffmpeg, disk, YouTube change).
- Limits: rate limit/bot check pauses the queue 90 s (`queue.rate_limited`); no ffmpeg -> progressive single-file only.
- Tests: `test_core.py`, `test_integration_local.py`. Owner rules: OR-009. Sources: `core/engine.py`, `core/queue.py`, `core/presets.py`.

## F-02 Audio quality choice
- Probe the link's audio streams (`core/audioprobe.py`); at or above 120 kbps a dialog offers MP3 (recommended), AAC/M4A, original stream, FLAC for lossless sources.
- MP3 is always 320 kbps; below that "no download" is the stated rule in `audioprobe` (`MP3_MIN_KBPS`). Tests: `test_core.py` (assumed; not verified per case).

## F-03 Playlists
- Playlist link opens a list (`PlaylistDialog.qml`, `audioprobe.probe_playlist`); single entries / Shift range / all; `playlist_items` spec to yt-dlp; saved in `Playlists\<name>\`
  numbered like the playlist with `<name>.html` (one player + list, `extras.write_playlist_page`). Gentle: 3-8 s between items.

## F-04 Album from tracklist (split chapters)
- If the description contains timestamps: offers Tracks only / Tracks + full file / No thanks. Tracks get names, tags (album, artist, track n/N), `.m3u8` (UTF-8 EXTENC, CRLF,
  single-line titles), chapters embedded. Cut shift 0.5 s earlier (`album.shift_cuts`, `install_cut_shift`). Tests: `test_album_page.py`, `test_core.py`.
- Limitation: albums downloaded before 0.8.13 need a re-download for the new page/m3u8 (REVIEW_AND_TODO item 10). VLC `.m3u8` reading **not confirmed** (open).

## F-05 Live stream recording
- Detects a running stream, asks whether/how long (until end, 15/30 min, 1/2 h, custom); `live_minutes`; needs ffmpeg and yt-dlp. Real-stream check outstanding (TODO.md).

## F-06 Extras (description, transcript, lyrics, MP3 tags, cover)
- `extras.write_extras`, `lyrics` (LRCLIB, https only, size cap, text fields only; fallback captions), `mp3tags.build_tag_data/auto_fill/read_tags/write_tags` (mutagen optional),
  "edit MP3 tags?" prompt default No (`ask_mp3_tags`). Tests: `test_lyrics.py`, `test_mp3tags.py`.

## F-07 HTML player page
- Local file player plus optional online player (`embed_url`: YouTube and Vimeo in code; Vimeo to be removed, D-020); `html_open_mode` file (default per README) or server (`core/localserve.py`, 127.0.0.1,
  only that folder, no listing). `html_create` server|file|both (settings default "both"). Test: `test_album_page.py`.
- **Note:** README says "Open page" defaults to the independent file, `Settings.html_open_mode` default is "server" -> contradiction C-04 in [12_PROJECT_STATE.md](12_PROJECT_STATE.md).

## F-08 TIDAL download
- `is_tidal_url` -> `Engine._run_tidal` -> `tidal.run_download` (tiddl subprocess, own `TIDDL_PATH` home, config from Settings via `config_toml`/`build_command`). After the download:
  `convert_to_mp3` for `normal` (AAC -> MP3 320, `.m4a` removed, M3U lists point to `.mp3`), optional HTML player pages (`write_html_pages`), folder button target (`downloaded_target`).
- Preconditions: tiddl found (`find_tiddl`: user path, then embedded, then `tiddl\` next to exe, PATH), signed in (`is_logged_in`), subscription. Errors via `classify`/`friendly_error`.
- Known: repeat download of a converted song fetches it again (CHANGELOG 0.9.1.24/26). Tests: `test_tidal.py` (fake tiddl; real ffmpeg for conversion).

## F-09 TIDAL DIY browse and playlist edit
- `TidalApi` (stdlib): `home/explore/feed/my_mixes/search/album/artist/playlist/mix/track/video/lyrics/favorites/user_playlists/stream`, writes: favorites, create/rename/delete
  playlist, add/remove tracks (with ETag). Token from tiddl `auth.json`; on 401 or expiry one `tiddl auth refresh`. Cache 5 min, max 2 parallel, page limit 50.
- UI: `TidalBackend.load(route, arg)` -> `pageLoaded/pageFailed`; every area fails alone. Tests: `test_tidal_api.py` (fake server), `test_tidal_gui_qml.py`.
- Unofficial API: endpoints checked against a real account on 2026-10-25 only.

## F-10 Players (TIDAL DIY, downloaded files)
- `TidalPlayer` (QMediaPlayer + QAudioOutput or own engine): queue (`QueueModel` move/remove/enqueue), shuffle/repeat, volume, lyrics (synced else text), quality badge, crossfade,
  loudness `SongProfile` (240 bins) for the band, drag and drop into queue/panel, `single_playback`. `LocalPlayer` plays files from downloads or music sources, library from finished audio jobs.
  Details: [modules/players.md](modules/players.md). Tests: `test_tidal_player.py`, `test_local_player.py`, `test_crossfade.py`.

## F-11 Own audio engine, sound check
- See [modules/audio_engine.md](modules/audio_engine.md). Tests `test_dsp.py`, `test_dsp_media.py`, `test_calibration.py`, `test_sound_settings.py`, `test_audio_outputs.py`.

## F-12 Stream to box
- SSDP discovery from every local IPv4, device XML, local HTTP server (own port, registered files only, random token, private clients only, Range), SOAP control (SetAVTransportURI,
  Play, Pause, Stop, SetVolume). Speaker card buttons steer the player in THIS PC (0.9.1.19). Tests `test_streaming.py` (2 failures known, see KI-002).

## F-13 Frame extractor
- ffmpeg splits a video into images every N seconds (max 5000 frames; < 1 s only for Shorts <= 180 s), JPG/PNG, `Frames\<video>\`; late preview results of a previous selection are discarded. Test `test_frames_preview.py`.

## F-14 External drives
- New USB/external drive offered as download target (name editable, default folder "Yeal"); small volumes skipped (virtual CD-like). `platforms/drives.py`. Test `test_drives.py`.

## F-15 yt-dlp self-update
- PyPI wheels (yt-dlp + yt-dlp-ejs) -> `<data>/ytdlp`, sha256 and zip-slip checks, atomic swap, check every 3 days, button in Settings. Test `test_updater.py`.

## F-16 Admin vault, login pack
- See [modules/security_and_logins.md](modules/security_and_logins.md). Tests `test_vault.py`, `test_loginpack.py`.

## F-17 Ad blocker (experimental, off by default)
- Local filter proxy on 127.0.0.1 (CONNECT host check only, no TLS interception) + page script; googlevideo.com never blocked; restart needed. Test `test_adblock.py`.

## F-18 History and duplicate check
- `history.save/load/find_done`, date groups (`section_label`), 500 newest. Test `test_history.py`.
