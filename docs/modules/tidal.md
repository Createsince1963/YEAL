# Module: TIDAL (`core/tidal.py`, `core/tidal_api.py`, `ui/tidal_backend.py`)

## `core/tidal.py` - tiddl helper (downloads only)
- Runs tiddl as a subprocess (`_popen`, `_env`); never imports tiddl. In the exe tiddl runs as `Yeal.exe --tiddl ...` (`EMBEDDED`, `command_prefix`, `embedded_available`).
- `find_tiddl(configured)`: user path -> embedded (frozen app prefers it over PATH) -> `tiddl\` next to exe -> PATH.
- Constants: `TIDAL_QUALITIES` normal/high/max, `TIDAL_VIDEO_QUALITIES` sd/hd/fhd, `TIDAL_VIDEOS` none/allow/only, `TIDAL_ATMOS`, `TIDAL_SINGLES` none/include/only, `TIDAL_HOSTS`, `NOTICE`.
- `build_command`, `config_toml(...)`, `prepare_home` (own `TIDDL_PATH` home, auth mirrored), `sync_auth_back` (newer token by `expires_at`), `run_download` (line classification, friendly errors),
  `new_audio_folders`, `convert_to_mp3` (ffmpeg, MP3 320, tags/cover kept, `.m4a` removed, progress per file), `downloaded_target`, `match_tracks`, `write_html_pages`, `logout`.
- Decisions: D-004, D-006, D-014, D-016. Tests: `tests/test_tidal.py`.

## `core/tidal_api.py` - catalogue and library
- stdlib only; token from tiddl auth (`load`, `valid`, `expired`, `refresh`); `request/get` with cache 5 min, max 2 parallel, timeouts; errors as `TidalError` per call.
- Uniform dicts (`kind,id,title,subtitle,cover,duration,explicit,quality,url`); read API and write API listed in [05_FUNCTIONS.md](../05_FUNCTIONS.md) F-09; `stream()` decodes the BTS manifest, prefers LOSSLESS/FLAC.
- Playlist writes use the TIDAL ETag. Tests: `tests/test_tidal_api.py`.

## `ui/tidal_backend.py`
- `TidalBackend`: `load(route,arg)`, favorites, playlist edits, `download(urls)`, `copyLink`, `saveLinklist(s)`, library refresh; ThreadPoolExecutor workers -> queued signals.
- `TidalPlayer`: shared base of both players ([players.md](players.md)); `SongProfile`, `QueueModel`, `buffer_levels`.
- Rule exception: QtMultimedia is imported lazily.
- Tests: `tests/test_tidal_player.py`, `tests/test_tidal_gui_qml.py`.

## Constraints
No fachliche TIDAL rule beyond OR-010 and OR-013 was added. Endpoints are unofficial (KI-015).
