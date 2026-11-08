# Tool: MediaOrbit player (player for downloaded files, sun view)

## Identity
Name: MediaOrbit player (sidebar button "Player"; code `LocalPlayerView.qml`, `ui/local_player.py`). Users: the owner. Status: built 0.9.1.11-0.9.1.38; sound/drag behaviour awaits hand tests.

## Problem and benefit
Play the finished audio downloads and any music folder (also on the network) with a good sound path, EQ, crossfade, outputs (Bluetooth), stream to a UPnP box, in the oval/solar-system design.

## Functions
- Core: library of finished audio jobs or a chosen music source, queue with drag and drop, Clear all / Save list, played list, song lists above/below, repeat/shuffle, volume, 10 s jumps, colours, loudness band, outer list ring, crossfade 3-10 s.
- Secondary: Folders planet (sources as moons), Speaker planet (audio output choice, stream to box controls), Sound planet (own engine: EQ, crossfeed, limiter, impulse response, buffer), Settings planet (sound check).
- Not included: lyrics for local files (KI-013), equalizer on the Qt engine, DSP chain for Stream to box.

## Domain logic
Library item naming from file stem (`split_name`, `library_items`); `LocalPlayer` inherits `TidalPlayer` (shared queue logic); `audio_engine` qt|dsp; `single_playback`. Rules: OR-005, OR-006.

## Inputs / outputs
In: downloads history, music sources, settings (`local_volume`, `sun_layout`, `queue_lists`, `library_source`, `crossfade`, `dsp` ...). Out: sound on the chosen output, saved queue lists, layout.

## Architecture
[../modules/players.md](../modules/players.md), [../modules/audio_engine.md](../modules/audio_engine.md).

## Operation
[06_WORKFLOWS.md](../06_WORKFLOWS.md) W-05, W-06.

## Tests
`test_local_player`, `test_music_sources`, `test_tidal_player`, `test_crossfade`, `test_dsp`, `test_dsp_media`, `test_calibration`, `test_sound_settings`, `test_audio_outputs`, `test_perfmon`, `test_gui_clipping`, `test_tidal_gui_qml`; benches `bench_player.py`, `bench_open_cards.py`. Not covered: real Bluetooth listening.

## History and next steps
Changelog 0.9.1.09-0.9.1.38. Open: KI-010 ... KI-013, hand-test list in [12_PROJECT_STATE.md](../12_PROJECT_STATE.md).
