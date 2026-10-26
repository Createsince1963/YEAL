"""Signal chain of Yeal's own audio engine (core/dsp.py): numbers, not listening."""
import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

import _path  # noqa: F401
from yeal.core import dsp

try:
    import numpy as np
except ImportError:
    np = None

FS = 48000.0


def tone(freq, seconds=0.5, fs=FS, amp=0.5):
    t = np.arange(int(fs * seconds)) / fs
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def rms_db(x):
    return 20 * math.log10(max(1e-12, float(np.sqrt(np.mean(np.square(x.astype(np.float64)))))))


def write_ir(path, samples, rate=48000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v)) * 32767)) for v in samples))


@unittest.skipUnless(np is not None, "numpy not installed")
class FilterDesignTests(unittest.TestCase):
    def test_peaking_filter_has_exactly_its_gain_at_the_centre(self):
        for gain in (-9.0, -3.0, 4.5, 12.0):
            mag = dsp.peaking_magnitude(np.array([1000.0]), FS, 1000.0, gain)[0]
            self.assertAlmostEqual(20 * math.log10(mag), gain, places=2)
        far = dsp.peaking_magnitude(np.array([30.0, 18000.0]), FS, 1000.0, 12.0)
        self.assertTrue(all(abs(20 * math.log10(m)) < 0.6 for m in far))

    def test_eq_fir_matches_the_wanted_response_and_is_linear_phase(self):
        gains = [0, 0, 0, 0, 0, 6.0, 0, 0, -6.0, 0]            # +6 dB at 1 kHz, -6 dB at 8 kHz
        h = dsp.design_eq(gains, 0.0, FS)
        self.assertEqual(len(h), dsp.EQ_TAPS + 1)
        self.assertTrue(np.allclose(h, h[::-1], atol=1e-12))    # exactly symmetric: linear phase, the same delay for every frequency
        spectrum = np.abs(np.fft.rfft(h, 1 << 16))
        freqs = np.fft.rfftfreq(1 << 16, 1.0 / FS)

        def at(f):
            return 20 * math.log10(spectrum[int(np.argmin(np.abs(freqs - f)))])
        self.assertAlmostEqual(at(1000), 6.0, delta=0.5)
        self.assertAlmostEqual(at(8000), -6.0, delta=0.5)
        self.assertAlmostEqual(at(100), 0.0, delta=0.5)
        self.assertAlmostEqual(at(16000), 0.0, delta=1.0)

    def test_preamp_moves_everything(self):
        h = dsp.design_eq([0] * 10, -6.0, FS)
        self.assertAlmostEqual(20 * math.log10(abs(np.sum(h))), -6.0, delta=0.3)

    def test_nothing_to_do_means_no_filter_and_no_delay(self):
        matrix, delay = dsp.build_matrix(dsp.DspConfig(), FS)
        self.assertIsNone(matrix)
        self.assertEqual(delay, 0)
        matrix, delay = dsp.build_matrix(dsp.DspConfig(eq_on=True), FS)               # on, but every band at 0
        self.assertIsNone(matrix)
        matrix, delay = dsp.build_matrix(dsp.DspConfig(eq_on=True, preamp=-3.0), FS)    # only a gain: no delay
        self.assertIsNotNone(matrix)
        self.assertEqual(delay, 0)
        self.assertAlmostEqual(float(matrix[0][0][0]), dsp.db(-3.0), places=6)
        matrix, delay = dsp.build_matrix(dsp.DspConfig(eq_on=True, eq=[0, 0, 0, 0, 0, 3, 0, 0, 0, 0]), FS)
        self.assertEqual(delay, dsp.EQ_TAPS // 2)

    def test_crossfeed_keeps_the_low_frequency_level_and_feeds_the_other_ear(self):
        for level in ("light", "medium", "strong"):
            direct, cross = dsp.crossfeed_paths(level, FS)
            self.assertAlmostEqual(float(np.sum(direct) + np.sum(cross)), 1.0, delta=0.02)    # a centred bass stays as loud
            self.assertGreater(float(np.sum(cross)), 0.0)
        light = float(np.sum(dsp.crossfeed_paths("light", FS)[1]))
        strong = float(np.sum(dsp.crossfeed_paths("strong", FS)[1]))
        self.assertLess(light, strong)
        self.assertIsNone(dsp.crossfeed_paths("off", FS))
        # high frequencies hardly cross over (the cross path is a low-pass)
        _, cross = dsp.crossfeed_paths("medium", FS)
        spectrum = np.abs(np.fft.rfft(cross, 4096))
        freqs = np.fft.rfftfreq(4096, 1.0 / FS)
        self.assertLess(spectrum[np.argmin(np.abs(freqs - 8000))], 0.2 * spectrum[np.argmin(np.abs(freqs - 100))])


@unittest.skipUnless(np is not None, "numpy not installed")
class ConvolverTests(unittest.TestCase):
    def test_block_convolution_equals_the_plain_convolution(self):
        rng = np.random.default_rng(1)
        matrix = rng.normal(size=(2, 2, 300)) * 0.1
        blocks = 5
        x = rng.normal(size=(blocks * dsp.BLOCK, 2)).astype(np.float32) * 0.3
        conv = dsp.Convolver(matrix)
        out = np.concatenate([conv.process(x[i * dsp.BLOCK:(i + 1) * dsp.BLOCK]) for i in range(blocks)])
        expect = np.zeros((blocks * dsp.BLOCK + 299, 2))
        for o in range(2):
            for i in range(2):
                expect[:, o] += np.convolve(x[:, i].astype(np.float64), matrix[o][i])
        self.assertTrue(np.allclose(out, expect[: len(out)], atol=2e-5))
        tail = conv.flush()                                                        # the rest of the filter after the last block
        self.assertEqual(len(tail), 299)
        self.assertTrue(np.allclose(tail, expect[len(out):], atol=2e-5))

    def test_a_long_impulse_response_works_across_block_boundaries(self):
        matrix = np.zeros((2, 2, 9000))
        matrix[0, 0, 8000] = 0.5
        matrix[1, 1, 8000] = 0.5
        x = np.zeros((3 * dsp.BLOCK, 2), dtype=np.float32)
        x[10, :] = 1.0
        conv = dsp.Convolver(matrix)
        out = np.concatenate([conv.process(x[i * dsp.BLOCK:(i + 1) * dsp.BLOCK]) for i in range(3)])
        self.assertAlmostEqual(float(out[8010, 0]), 0.5, places=5)                 # 8000 frames later, two blocks on
        self.assertAlmostEqual(float(np.abs(out).sum() - 1.0), 0.0, places=4)


@unittest.skipUnless(np is not None, "numpy not installed")
class ChainTests(unittest.TestCase):
    def run_chain(self, cfg, signal, volume=1.0, gain_db=0.0):
        chain = dsp.Chain(cfg, FS)
        chain.volume = volume
        chain.set_replaygain(gain_db)
        n = len(signal) // dsp.BLOCK * dsp.BLOCK
        out = np.concatenate([chain.process(signal[i:i + dsp.BLOCK]) for i in range(0, n, dsp.BLOCK)])
        return chain, out

    def stereo(self, mono):
        return np.stack([mono, mono], axis=1).astype(np.float32)

    def test_without_effects_the_music_passes_untouched(self):
        x = self.stereo(tone(440, 1.0))
        chain, out = self.run_chain(dsp.DspConfig(), x)
        self.assertIsNone(chain.convolver)
        self.assertEqual(chain.delay, 0)
        self.assertTrue(np.array_equal(out, x[: len(out)]))

    def test_volume_and_replaygain_are_gains(self):
        x = self.stereo(tone(440, 1.0, amp=0.2))
        _, out = self.run_chain(dsp.DspConfig(replaygain="track"), x, volume=0.5, gain_db=6.0)
        self.assertAlmostEqual(rms_db(out) - rms_db(x[: len(out)]), 6.0 - 6.02, delta=0.05)
        _, out = self.run_chain(dsp.DspConfig(replaygain="off"), x, volume=1.0, gain_db=6.0)
        self.assertAlmostEqual(rms_db(out) - rms_db(x[: len(out)]), 0.0, delta=0.01)        # switched off: no gain

    def test_limiter_bends_peaks_instead_of_clipping(self):
        x = self.stereo(tone(300, 1.0, amp=1.8))
        _, out = self.run_chain(dsp.DspConfig(limiter=True), x)
        self.assertLessEqual(float(np.abs(out).max()), 1.0)
        self.assertGreater(float(np.abs(out).max()), 0.95)
        quiet = self.stereo(tone(300, 0.5, amp=0.5))
        _, same = self.run_chain(dsp.DspConfig(limiter=True), quiet)
        self.assertTrue(np.array_equal(same, quiet[: len(same)]))                           # below the threshold: untouched
        _, hard = self.run_chain(dsp.DspConfig(limiter=False), x)
        self.assertGreater(float(np.abs(hard).max()), 1.5)

    def test_equalizer_boosts_only_its_band(self):
        eq = [0, 0, 0, 0, 0, 6.0, 0, 0, 0, 0]
        cfg = dsp.DspConfig(eq_on=True, eq=eq)
        for freq, expected in ((1000, 6.0), (100, 0.0), (10000, 0.0)):
            x = self.stereo(tone(freq, 1.0, amp=0.1))
            chain, out = self.run_chain(cfg, x)
            settled = out[dsp.EQ_TAPS * 2:, 0]                                              # after the filter has filled
            self.assertAlmostEqual(rms_db(settled) - rms_db(x[dsp.EQ_TAPS * 2: len(out), 0]), expected, delta=0.6, msg=freq)
        self.assertEqual(chain.delay, dsp.EQ_TAPS // 2)

    def test_crossfeed_puts_a_part_of_one_ear_into_the_other(self):
        x = np.stack([tone(200, 1.0), np.zeros(int(FS))], axis=1).astype(np.float32)       # left only
        _, out = self.run_chain(dsp.DspConfig(crossfeed="medium"), x)
        left, right = out[8000:, 0], out[8000:, 1]
        self.assertGreater(rms_db(right), -40.0)                                            # the right ear hears something now
        self.assertLess(rms_db(right), rms_db(left) - 3.0)                                  # but clearly less
        _, mono = self.run_chain(dsp.DspConfig(crossfeed="medium"), self.stereo(tone(200, 1.0)))
        self.assertAlmostEqual(rms_db(mono[8000:, 0]), rms_db(tone(200, 1.0)[8000:len(mono)]), delta=0.7)   # centred stays about as loud

    def test_convolution_with_an_impulse_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            ir = Path(tmp) / "ir.wav"
            samples = [0.0] * 120 + [0.5]
            write_ir(ir, samples)
            cfg = dsp.DspConfig(convolution_on=True, convolution=str(ir))
            x = np.zeros((dsp.BLOCK * 2, 2), dtype=np.float32)
            x[5, :] = 1.0
            chain, out = self.run_chain(cfg, x)
            self.assertEqual(chain.delay, 120)
            self.assertAlmostEqual(float(out[125, 0]), 0.5, places=3)
            self.assertAlmostEqual(float(out[125, 1]), 0.5, places=3)
            # another sample rate in the file: it is resampled to the rate of the engine
            write_ir(ir, [0.0] * 2400 + [0.5], rate=24000)                                   # a delta after 0.1 s at 24 kHz
            matrix, delay = dsp.build_matrix(cfg, FS)
            self.assertAlmostEqual(delay, 4800, delta=3)

    def test_a_broken_impulse_response_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.wav"
            bad.write_bytes(b"not a wave file")
            self.assertIsNone(dsp.load_impulse_response(str(bad), FS))
            self.assertIsNone(dsp.load_impulse_response(str(Path(tmp) / "missing.wav"), FS))
            matrix, delay = dsp.build_matrix(dsp.DspConfig(convolution_on=True, convolution=str(bad)), FS)
            self.assertIsNotNone(matrix)                                                     # still a valid (identity) filter
            self.assertEqual(delay, 0)

    def test_the_tail_is_flushed(self):
        cfg = dsp.DspConfig(eq_on=True, eq=[0, 0, 0, 0, 0, 6.0, 0, 0, 0, 0])
        chain = dsp.Chain(cfg, FS)
        chain.process(np.ones((dsp.BLOCK, 2), dtype=np.float32) * 0.1)
        tail = chain.flush()
        self.assertEqual(len(tail), dsp.EQ_TAPS)                                              # the filter has EQ_TAPS + 1 taps
        self.assertEqual(len(chain.flush()), dsp.EQ_TAPS)                                     # flushing again gives silence of the same length
        self.assertEqual(float(np.abs(chain.flush()).max()), 0.0)

    def test_a_short_last_block_keeps_its_length(self):
        chain = dsp.Chain(dsp.DspConfig(eq_on=True, eq=[0, 0, 0, 0, 0, 3.0, 0, 0, 0, 0]), FS)
        out = chain.process(np.zeros((1000, 2), dtype=np.float32))
        self.assertEqual(out.shape, (1000, 2))


class ConfigAndGainTests(unittest.TestCase):
    def test_config_is_cleaned(self):
        cfg = dsp.validate_config({"eq": [20, -20, "x", None, 1.234] + [0] * 3, "preamp": 99, "crossfeed": "huge",
                                   "replaygain": "album", "convolution": "C:/ir.wav", "junk": 1, "eq_on": 1})
        self.assertEqual(cfg["eq"], [12.0, -12.0, 0.0, 0.0, 1.2, 0.0, 0.0, 0.0, 0.0, 0.0])   # ten bands, limited, rounded
        self.assertEqual(cfg["preamp"], 12.0)
        self.assertEqual(cfg["crossfeed"], "off")
        self.assertEqual(cfg["replaygain"], "off")
        self.assertIs(cfg["eq_on"], True)
        self.assertNotIn("junk", cfg)
        self.assertEqual(dsp.validate_config(None)["eq"], [0.0] * 10)
        self.assertEqual(dsp.validate_config({"eq": [float("nan")] * 10})["eq"], [0.0] * 10)
        self.assertTrue(dsp.validate_config({})["limiter"])                                    # on by default

    def test_replaygain(self):
        self.assertAlmostEqual(dsp.replaygain_db(-22.0), 6.0)                                  # quiet song: louder
        self.assertAlmostEqual(dsp.replaygain_db(-10.0), -6.0)                                 # loud song: quieter
        self.assertEqual(dsp.replaygain_db(-60.0), 12.0)                                       # limited
        self.assertEqual(dsp.replaygain_db(-95.0), 0.0)                                        # silence: nothing to measure
        self.assertEqual(dsp.replaygain_db(None), 0.0)

    def test_available(self):
        self.assertEqual(dsp.available(), np is not None)


if __name__ == "__main__":
    unittest.main()
