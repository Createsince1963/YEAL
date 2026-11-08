# Module: players and sun view

## Classes (verified by reading the class list, 2026-11-07)
- `ui/tidal_backend.py`: `TidalPlayer(QObject)` (queue, play/pause/seek, shuffle/repeat, volume, lyrics, badge, levels, crossfade hooks, `enqueue`, `playNow`, `replay(i)`, `upcoming(n)`), `QueueModel` (move/remove/clear, stable shuffle order), `SongProfile` (240-bin loudness profile).
- `ui/local_player.py`: `LocalPlayer(TidalPlayer)`, `LocalOwner` (QML-facing owner), `library_items(jobs)`, `split_name(stem, tidal_job, uploader)`.
- `ui/crossfade.py`: `Crossfader` with phase functions (`phase_before`, `phase_after`) - seamless change; next TIDAL stream is fetched 1.5 s before the fade.
- QML: `SunView.qml` (generic), wrappers `LocalPlayerView.qml`, `TidalSunView.qml`; `Planet.qml`, `PlanetCard.qml`, `SunFan.qml`, `SunSources/Speaker/Sound/Settings.qml`, `TidalTrackPlayer.qml` (oval), `TidalTrackPanel.qml`, `TidalPlayerBar.qml` (classic bar).

## Behaviour that is easy to break
- Cards open on the side of their planet (`zoneOf`), also after the planet was dragged; cards of one side share the side in planet order.
- Edit-mode zoom (`edit: true`) for cards; queue card has Clear all and Save list; saved lists live in `queue_lists` (max 30 x 2000).
- Level band: `song` mode uses the full-song profile (local files can be scanned completely with `QAudioDecoder`, at most 6 ms of GUI thread at a time); `flow` is the running level; real levels only, no invented animation.
- Repaint limits: oval at most 20 Hz (`ui_refresh_hz` 10-30), not while hidden; the sun glow is one small picture scaled with a transform; cards must open in ~45 ms (benchmark `bench_open_cards.py`).
- `single_playback`: DIY playing pauses web players; switching pauses the other player.
- Volume: separate settings `tidal_volume` and `local_volume`; Windows volume stays separate (KI-011).

## Tests
`test_tidal_player.py`, `test_local_player.py`, `test_crossfade.py`, `test_music_sources.py`, `test_tidal_gui_qml.py`, `test_gui_clipping.py`, `test_qml_smoke.py`.
