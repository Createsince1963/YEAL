# 04 Data model

Sources: `core/models.py`, `core/settings.py`, `core/history.py`, `core/vault.py`, `core/loginpack.py`, `core/music_sources.py`, `core/tidal_api.py`.
Format per object follows protocol section 8 (shortened where a field does not apply).

## DownloadOptions (per job)
- Meaning: all choices for one download; built by `Settings.to_options()` from the active profile plus global limits. Dataclass, `normalized()` coerces invalid values.
- Fields (default): `mode` video|audio (video), `max_height` 0/2160/1440/1080/720/480/360 (1080), `audio_format` mp3|m4a|opus|flac|best (mp3),
  `audio_bitrate` 128/192/256/320 (320; forced 320 for mp3), `embed_metadata` (True), `subtitles`, `sub_langs` (de, en), `playlist`, `save_description`,
  `save_transcript`, `online_player`, `split_chapters`, `html_theme` light|dark|auto, `rate_limit_kbps`, `proxy`, `profile`, `custom` (dict, sanitized),
  `cookies_browser` ""|firefox|edge|chrome, `gentle` (True), `save_lyrics`, `keep_whole` (True), `live_minutes` (0..1440), `playlist_dir`, `playlist_items`
  (spec like `1,3,5-7`), `html_create` server|file|both, `single_playback` (True), `tidal_quality` ""|normal|high|max, `cookies_file` (max 500 chars).
- Validation: `normalized()`; `custom` filtered by `FORBIDDEN_KEYS` in `presets.py`.
- Persistence: embedded in history entries (see below); never stored alone.

## DownloadJob
- Meaning: one queue entry. Identifier: `id` (int, assigned by the queue). Relations: owns one `DownloadOptions`.
- Fields: `url`, `state` (JobState), `title`, `progress` (0..1 overall), `dl_progress`, `pp_progress`, `phase`, `speed`, `eta`, `filename`, `error` (plain language),
  `error_detail` (technical line), `playlist_index/count`, `thumbnail`, `uploader`, `duration`, `size`, `has_/saved_description`, `has_/saved_transcript`, `note`
  (things skipped), `saved_lyrics` ""|lyrics|captions, `tags_ask`, `created` (epoch).
- Lifecycle: queued -> fetching -> downloading -> processing -> done|error|canceled; `retry` calls `reset()`; `remove` deletes from the list only (files stay).
- Persistence: only finished jobs, newest 500, in `history.json` (`core/history.py`, tolerant loading).

## Settings (`settings.json`)
- Dataclass `Settings`, JSON, atomic writes, tolerant loading, `validate()` clamps every value (ranges in code). About 90 fields in groups:
  general (`theme` system|light|dark, `max_parallel` 1-4, `gentle_mode`, `auto_update`, `download_dir`, `rate_limit_kbps`, `proxy`, `custom_options`),
  login (`cookies_browser`, `cookies_file`), helpers (`ffmpeg_path`, `node_path`, `tidal_path`), TIDAL download (`tidal_quality`, `tidal_threads` 1-4,
  `tidal_video_quality` sd|hd|fhd, `tidal_videos`, `tidal_atmos`, `tidal_singles`, `tidal_lyrics/lrc/cover_embed/cover_file/m3u/html/no_skip/rewrite`),
  TIDAL DIY / players (`tidal_volume`, `tidal_tile_size` 90-260, `tidal_player_style` bar|track, `tidal_player_color`, `tidal_player_vis_mode`, `tidal_sun`,
  `tidal_layout` dict, `local_volume`, `sun_scale` 0.5-3, `sun_layout` dict, `glow_amp` 0-300, `level_amp` 50-300, `outer_ring`, `custom_colors` max 5, `crossfade` 0|3-10,
  `local_orbit`, `library_source`, `music_sources`, `queue_lists`), audio (`audio_engine` qt|dsp, `dsp` dict, `audio_buffer_ms` 200-2000 (600),
  `ui_refresh_hz` 10-30 (20), `audio_output`), HTML (`html_open_mode` file|server, `html_create`, `single_playback`), streaming (`stream_device`, `stream_hosts`
  max 10, `stream_volume` -1..100, `stream_scan_seconds`, `stream_port`), UI state (`panel_width`, `panel_right`, `show_browser`, `dl_button_style/pos`, `ui_collapsed`,
  `list_group`, `window`, `drive_ignored`, `drive_folder`, `ask_drive_dialog`, `ask_mp3_tags`, `setup_complete`), `profiles`, `active_profile`, `profiles_version` (2).
- Defaults of note: `tidal_quality` "high", `theme` "system", `active_profile` "Video 1080p", `max_parallel` 2.
- Change rule: UI edits on the Settings page are staged and saved/discarded explicitly; layout settings (panel width, `tidal_layout`) save immediately without the dialog.
  `Backend.setSetting` converts `QJSValue` objects from QML (before 0.9.1.05 object values were dropped silently).
- Full field list: `core/settings.py` (single source of truth for ranges).

## Profile (inside `Settings.profiles`)
Keys: `name` (unique case-insensitive, max 40), `mode`, `max_height`, `audio_format`, `embed_metadata`, `subtitles`, `playlist`, `save_description`, `save_transcript`,
`online_player`, `split_chapters`, `save_lyrics`, `keep_whole`, `audio_bitrate`. Defaults: Video 4K, Video 1080p, Video 720p, Video best, Audio MP3, Audio original.

## Track / queue item (TIDAL DIY and local player)
Uniform dict from `tidal_api`: `kind, id, title, subtitle, cover, duration, explicit, quality, url` (canonical `https://tidal.com/browse/<kind>/<id>`);
local items add `file`, `source`. Saved queue list: `{name (unique, max 60), items[{kind:"track", id, title, subtitle, file, cover, duration, url, source}]}`, max 30 lists x 2000 items.
Music source: `{id, name, path, kind local|network}` (`core/music_sources.validate_sources`).

## Layout data
`sun_layout`: `{ "<view>.<planet>": {deg 0..360, r 0.4..3} }`, max 40. `tidal_layout`: `{player: top|bottom, playlists|queue: {dock left|right|float|hidden, w 160..900,
(float) x,y,h}}`. Window outside all screens is moved back by QML.

## Files in the data folder
| File | Content | Written by |
|---|---|---|
| `settings.json` | Settings | `core/settings.py` |
| `history.json` | last 500 finished jobs | `core/history.py` |
| `vault.json` | encrypted logins + verifier | `core/vault.py` |
| `ytdlp\`, `stamp.json` | self-updated yt-dlp (+ejs) wheels, check time | `core/updater.py` |
| `tiddl\config.toml`, `tiddl\auth.json` | isolated tiddl home; auth mirrored from `~/.tiddl`, newer one written back by `expires_at` | `core/tidal.py` |
| `youtube_cookies.txt` | own copy of the chosen cookie file | backend |
| `audio_profile.json`, `audio_report.json` | calibration result | `ui/calibration.py` |
| `blocklist.txt` | optional hosts-format list for the ad blocker | user |
| `*.yealpack` | login pack, wherever the user saves it | `core/loginpack.py` |
| `yeal.log`, `yeal.prev.log` | log (frozen exe or `YEAL_LOG=1`) | `main.py` |

## Output folders (in the download folder)
`Video\`, `Audio\`, `Playlists\<name>\` (+ `<name>.html`), album folders with `.m3u8`, `Frames\<video>\`, `Tidal\` (singles, playlists, videos) and `Tidal\Linklisten\<name>.html`.
Exact TIDAL sub-folder names come from tiddl's output template (`tidal.output_template`) - not re-verified here.

## Rules that protect data (copy / move / delete)
- Identity and origin of downloads are not altered by Yeal after the fact except documented steps (MP3 conversion removes the `.m4a`, OR-010).
- HTML pages and link lists do not overwrite existing files silently.
- Deleting a job removes the list entry only. "Delete all logins" in the admin area also wipes the browser sign-in (README).
- Secrets: see [modules/security_and_logins.md](modules/security_and_logins.md).
