# Module: own audio engine, calibration, outputs

## Chain
`ffmpeg (decode, resample) -> core/dsp.py chain (float32) -> QAudioSink (WASAPI) -> Windows / Bluetooth -> speakers`. Windows keeps the Bluetooth connection; Python only does the maths.
- `core/dsp.py`: 10-band equalizer with pre-amp (linear phase FIR), crossfeed for headphones, ReplayGain-like loudness, convolution with an impulse response (room/headphone correction), soft limiter;
  one FIR matrix per sample rate applied with overlap-add FFT in blocks; needs numpy; `available()` is False without it and Yeal plays through Qt. Config validated by `dsp.validate_config` (setting `dsp`).
- `ui/dsp_media.py`: `DspMedia`, `_Feed` (bounded queues, 160 chunks), `usable(ffmpeg)`; counts `underruns`; longest chain tick measured; engine switch without a stop.
- `core/audiodev.py`: classifies outputs (headphones/monitor/speaker) for icon and order; `audio_output` setting; Bluetooth hands-free warning.
- `ui/calibration.py`, `calibration_runner.py`, `Calibrate_Yeal.bat`: tests the real chain on the chosen output (smallest buffer without dropout 200-1500 ms, recommends one step above; repaint rate 15/20 Hz from GUI lag;
  `--stress` with 40 song changes checks threads, ffmpeg processes, memory, dropouts, lag); writes `audio_profile.json`, `audio_report.json`; `--apply` writes the settings. The Settings planet runs it as its own process.
- `ui/perfmon.py` (`YEAL_PERF=1`): CPU, RAM, ffmpeg, threads, GUI lag every 2 s.

## Facts and limits
- The chain runs in the GUI thread: a busy GUI starves the buffer (`audio_buffer_ms`, default 600). Measured (0.9.1.25/.26): DSP costs 0.4 ms per 85 ms block, level calc 0.1 ms; no leak in 30 song changes; first calibration: no dropout from 200 ms, GUI lag max 113 ms.
- Not in the exe: numpy. Open: KI-005, KI-012. Rule: OR-006.

## Tests
`test_dsp`, `test_dsp_media`, `test_calibration`, `test_sound_settings`, `test_audio_outputs`, `test_perfmon`.
