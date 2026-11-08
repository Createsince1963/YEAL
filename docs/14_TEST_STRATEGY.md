# 14 Test strategy

Facts from `tests\`, `Test_Yeal.bat`, CLAUDE.md, HANDOFF. **No test was run during the initialisation** (no code was changed; GUI-style suites need the owner's release per protocol phase D). Pass/fail status of today's tree is therefore unknown.

## Commands
Run ONE test file at a time (several Qt engines in one process crash). From `tests\`, with the central Python:
```bat
set QT_QPA_PLATFORM=offscreen
set QT_QUICK_BACKEND=software
C:\Users\mail\AI_Coworker_Claude\Tools_Central\Python\python\python.exe -m unittest test_core
```
`Test_Yeal.bat` runs `unittest discover` (crashes, KI-001). Static check: `git diff --check` (protocol phase D).
After a card or button change always run `test_gui_clipping`, `test_qml_smoke`, `test_tidal_gui_qml`.

## Suites (static count of `def test_` per file)
| Area | Files (tests) |
|---|---|
| Core download pipeline | `test_core` (57), `test_integration_local` (7), `test_history` (7), `test_updater` (7), `test_drives` (7), `test_adblock` (4), `test_frames_preview` (2) |
| Extras | `test_lyrics` (13), `test_mp3tags` (22), `test_album_page` (5) |
| TIDAL | `test_tidal` (40, fake tiddl + real ffmpeg conversion), `test_tidal_api` (20, fake HTTP server), `test_tidal_player` (40), `test_tidal_gui_qml` (19) |
| Players / audio | `test_local_player` (7), `test_music_sources` (5), `test_crossfade` (11), `test_dsp` (19), `test_dsp_media` (8), `test_sound_settings` (5), `test_audio_outputs` (5), `test_calibration` (9), `test_perfmon` (2) |
| Security | `test_vault` (5), `test_loginpack` (5) |
| Streaming | `test_streaming` (18; two known failures, KI-002) |
| GUI | `test_qml_smoke` (1), `test_gui_clipping` (1, Flow lays out only inside a QQuickWindow), `test_default_gui` (4), `test_settings_layout` (5) |
| Benchmarks (not tests) | `bench_player.py`, `bench_open_cards.py` |

Last recorded totals: 120 passed, 1 skipped at 0.8.x (REVIEW_AND_TODO). No later total is documented.

## Principles used by the project
- Fake external systems: fake tiddl executable, fake TIDAL HTTP server, fake renderers; no real account needed in CI.
- QML components are loaded offscreen and must produce no warnings.
- Generated audio buffers / sine files for the level path; real ffmpeg for conversion.
- Real-music and real-account behaviour is hand-tested by the owner (list in [12_PROJECT_STATE.md](12_PROJECT_STATE.md)).

## Test limits
No test covers: a signed-in TIDAL account, real playback on Bluetooth, drag from the TIDAL Web view (WebView2), the built exe, Android. GUI performance on the real GPU is not measured by the offscreen software renderer.

## Required per change type (project rule + protocol)
| Change | Minimum |
|---|---|
| `core/*.py` | its own test file + `test_core` |
| Settings keys | `test_core`/`test_settings_layout`/`test_sound_settings` (whichever owns the key) |
| QML card/button | `test_gui_clipping`, `test_qml_smoke`, `test_tidal_gui_qml` |
| TIDAL | `test_tidal`, `test_tidal_api`, `test_tidal_player` |
| Audio | `test_dsp`, `test_dsp_media`, `test_crossfade`, `test_calibration` |
Plus: docs updated, `git diff --check`, version files consistent.

## Open question
Whether offscreen QML test runs count as "GUI tests" under the protocol (needing release) - see owner question Q-03.
