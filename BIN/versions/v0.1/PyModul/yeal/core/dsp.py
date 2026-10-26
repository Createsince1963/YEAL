"""Signal chain of Yeal's own audio engine (desktop, optional): 32-bit float DSP between the decoder and the sound card.

    ffmpeg (decode, resample) -> this chain -> Qt audio sink (WASAPI on Windows) -> Windows / Bluetooth -> headphones

Windows keeps the Bluetooth connection; Python only does the maths. The chain has: a 10 band equalizer with pre-amp (linear
phase, built as an FIR filter), crossfeed for headphones, ReplayGain-like loudness, convolution with an impulse response
(room or headphone correction) and a soft limiter against clipping.

Everything that filters is one FIR matrix per sample rate (equalizer x crossfeed x impulse response), applied with overlap-add
FFT convolution in blocks. Needs numpy; without it `available()` is False and Yeal keeps playing through Qt.
No Qt in this file.
"""
from __future__ import annotations

import math
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

try:                                   # numpy is optional: without it the engine is simply not offered
    import numpy as np
except ImportError:                    # pragma: no cover - the dev machine has numpy
    np = None

EQ_BANDS = (31.0, 62.0, 125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0)    # centre frequencies in Hz
EQ_Q = 1.41                            # about one octave wide per band
EQ_LIMIT_DB = 12.0
EQ_TAPS = 4096                         # design length of the equalizer FIR: it has EQ_TAPS + 1 taps (symmetric, linear phase), delay EQ_TAPS // 2
CROSSFEED = {"off": None, "light": -9.0, "medium": -6.0, "strong": -3.5}     # level of the cross path at low frequencies (dB)
REPLAYGAIN_TARGET_DB = -16.0           # a typical RMS level of mastered music
BLOCK = 4096                           # frames per block
MAX_IR_SECONDS = 1.5


def available() -> bool:
    return np is not None


# ---------------------------------------------------------------------------------------------------------------- config

@dataclass
class DspConfig:
    eq_on: bool = False
    eq: List[float] = field(default_factory=lambda: [0.0] * len(EQ_BANDS))     # dB per band
    preamp: float = 0.0                                                          # dB, comes before the bands
    crossfeed: str = "off"                                                       # off | light | medium | strong
    replaygain: str = "off"                                                      # off | track
    convolution_on: bool = False
    convolution: str = ""                                                        # path of a WAV impulse response
    limiter: bool = True

    @property
    def filtering(self) -> bool:
        """True if any FIR is needed (otherwise only gains and the limiter are applied: no delay)."""
        return (self.eq_on and (any(abs(g) > 0.05 for g in self.eq) or abs(self.preamp) > 0.05)) \
            or self.crossfeed != "off" or (self.convolution_on and bool(self.convolution))


def validate_config(raw) -> dict:
    """The settings dict of the engine, cleaned: unknown keys dropped, numbers limited, 10 EQ values."""
    raw = raw if isinstance(raw, dict) else {}
    base = DspConfig()
    out = {"eq_on": bool(raw.get("eq_on", base.eq_on)), "limiter": bool(raw.get("limiter", base.limiter)),
           "convolution_on": bool(raw.get("convolution_on", False))}
    eq = raw.get("eq")
    values = []
    for i in range(len(EQ_BANDS)):
        try:
            v = float(eq[i]) if isinstance(eq, (list, tuple)) and i < len(eq) else 0.0
        except (TypeError, ValueError):
            v = 0.0
        values.append(round(max(-EQ_LIMIT_DB, min(EQ_LIMIT_DB, v if v == v else 0.0)), 1))
    out["eq"] = values
    try:
        pre = float(raw.get("preamp", 0.0))
    except (TypeError, ValueError):
        pre = 0.0
    out["preamp"] = round(max(-EQ_LIMIT_DB, min(EQ_LIMIT_DB, pre if pre == pre else 0.0)), 1)
    out["crossfeed"] = raw.get("crossfeed") if raw.get("crossfeed") in CROSSFEED else "off"
    out["replaygain"] = raw.get("replaygain") if raw.get("replaygain") in ("off", "track") else "off"
    out["convolution"] = str(raw.get("convolution") or "")[:400]
    return out


def config_from(raw) -> DspConfig:
    return DspConfig(**validate_config(raw))


# ------------------------------------------------------------------------------------------------------ filter design

def db(x: float) -> float:
    return 10.0 ** (x / 20.0)


def peaking_magnitude(freqs, fs: float, f0: float, gain_db: float, q: float = EQ_Q):
    """Magnitude of an RBJ peaking filter at `freqs` (Hz); exact, evaluated on the unit circle."""
    a = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f0 / fs
    alpha = math.sin(w0) / (2.0 * q)
    b = np.array([1.0 + alpha * a, -2.0 * math.cos(w0), 1.0 - alpha * a])
    c = np.array([1.0 + alpha / a, -2.0 * math.cos(w0), 1.0 - alpha / a])
    w = 2.0 * np.pi * np.asarray(freqs, dtype=np.float64) / fs
    z1, z2 = np.exp(-1j * w), np.exp(-2j * w)
    return np.abs((b[0] + b[1] * z1 + b[2] * z2) / (c[0] + c[1] * z1 + c[2] * z2))


def eq_magnitude(freqs, fs: float, gains_db, preamp_db: float = 0.0):
    mag = np.full(len(freqs), db(preamp_db), dtype=np.float64)
    for f0, g in zip(EQ_BANDS, gains_db):
        if abs(g) > 0.05 and f0 < fs / 2.0:
            mag *= peaking_magnitude(freqs, fs, f0, g)
    return mag


def design_eq(gains_db, preamp_db: float, fs: float, taps: int = EQ_TAPS):
    """Linear-phase FIR with the response of the equalizer: taps + 1 values, exactly symmetric around the middle, so every
    frequency is delayed by the same taps // 2 frames."""
    n = taps
    freqs = np.fft.rfftfreq(n, 1.0 / fs)
    mag = eq_magnitude(freqs, fs, gains_db, preamp_db)
    h = np.fft.irfft(mag, n)                  # zero phase, symmetric around index 0 (circular)
    h = np.roll(h, n // 2)                    # the middle is now index n / 2 ...
    h = np.append(h, h[0])                    # ... and one more tap makes the whole thing symmetric around it
    return (h * np.blackman(n + 1)).astype(np.float64)


def crossfeed_paths(level: str, fs: float):
    """(direct, cross) FIRs of a Bauer-like crossfeed: the other ear gets a low-passed (700 Hz), slightly delayed and
    attenuated copy, the direct path is lowered a little so that the loudness stays. Returns None for 'off'."""
    cross_db = CROSSFEED.get(level)
    if cross_db is None:
        return None
    n = 256
    delay = max(1, int(round(0.00028 * fs)))                  # 0.28 ms: the extra way around the head
    a = math.exp(-2.0 * math.pi * 700.0 / fs)                 # one-pole low-pass
    lp = (1.0 - a) * a ** np.arange(n - delay, dtype=np.float64)
    cross = np.zeros(n)
    cross[delay:] = lp * db(cross_db)
    direct = np.zeros(n)
    direct[0] = 1.0 / (1.0 + db(cross_db))                    # the sum of both paths at low frequencies stays about 1
    return direct, cross * (1.0 / (1.0 + db(cross_db)))


def load_impulse_response(path: str, fs: float):
    """(left, right) float arrays of a WAV impulse response, resampled to `fs` (linear interpolation) and at most 1.5 s long,
    normalised so that its loudest point is not louder than the input. Mono is used for both ears. None if it cannot be read."""
    try:
        with wave.open(str(path), "rb") as w:
            channels, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            raw = w.readframes(min(frames, int(MAX_IR_SECONDS * rate)))
    except (OSError, EOFError, wave.Error):
        return None
    if width == 2:
        data = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    elif width == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        v = np.where(v >= 1 << 23, v - (1 << 24), v)
        data = v.astype(np.float64) / (1 << 23)
    elif width == 4:
        data = np.frombuffer(raw, dtype="<i4").astype(np.float64) / 2147483648.0
    elif width == 1:
        data = (np.frombuffer(raw, dtype=np.uint8).astype(np.float64) - 128.0) / 128.0
    else:
        return None
    if channels < 1 or len(data) < channels:
        return None
    data = data[: len(data) // channels * channels].reshape(-1, channels)
    left, right = data[:, 0], data[:, 1] if channels > 1 else data[:, 0]
    if rate != fs:
        n = max(2, int(round(len(left) * fs / rate)))
        x = np.linspace(0.0, len(left) - 1, n)
        left, right = np.interp(x, np.arange(len(left)), left), np.interp(x, np.arange(len(right)), right)
    peak = max(float(np.sum(np.abs(left))), float(np.sum(np.abs(right))), 1e-9)
    scale = 1.0 / peak if peak > 1.0 else 1.0                 # an IR that would raise the level is turned down
    return left * scale, right * scale


def fft_convolve(a, b):
    """Full convolution of two 1-D arrays with the FFT."""
    n = len(a) + len(b) - 1
    size = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(a, size) * np.fft.rfft(b, size), size)[:n]


def build_matrix(cfg: DspConfig, fs: float):
    """The 2x2 FIR matrix of the whole filtering (equalizer, crossfeed, impulse response): M[out][in], all of one length,
    plus the delay in frames that the filtering adds (for the position display). None when nothing needs filtering."""
    if not cfg.filtering:
        return None, 0
    delay = 0
    eq = np.array([1.0])
    if cfg.eq_on:
        if any(abs(g) > 0.05 for g in cfg.eq):
            eq = design_eq(cfg.eq, cfg.preamp, fs)                  # the bands (and the pre-amp) as a linear-phase FIR
            delay += (len(eq) - 1) // 2
        elif abs(cfg.preamp) > 0.05:
            eq = np.array([db(cfg.preamp)])                         # only the pre-amp: a plain gain, no delay
    cf = crossfeed_paths(cfg.crossfeed, fs)
    if cf is None:
        direct, cross = np.array([1.0]), np.array([0.0])
    else:
        direct, cross = cf
    m = [[fft_convolve(eq, direct), fft_convolve(eq, cross)],
         [fft_convolve(eq, cross), fft_convolve(eq, direct)]]
    if cfg.convolution_on and cfg.convolution:
        ir = load_impulse_response(cfg.convolution, fs)
        if ir is not None:
            left, right = ir
            m = [[fft_convolve(m[0][0], left), fft_convolve(m[0][1], left)],
                 [fft_convolve(m[1][0], right), fft_convolve(m[1][1], right)]]
            delay += int(max(np.argmax(np.abs(left)), np.argmax(np.abs(right))))
    length = max(len(x) for row in m for x in row)
    out = [[np.pad(x, (0, length - len(x))) for x in row] for row in m]
    return np.array(out), delay                                # shape (2, 2, length)


# ---------------------------------------------------------------------------------------------------------- processing

class Convolver:
    """Overlap-add FFT convolution of a stereo stream with a 2x2 FIR matrix, block by block (BLOCK frames in, BLOCK out)."""
    def __init__(self, matrix, block: int = BLOCK):
        self.block = block
        self.length = matrix.shape[2]
        self.size = 1 << (block + self.length - 2).bit_length()
        self.spectra = np.fft.rfft(matrix, self.size, axis=2)            # (out, in, bins)
        self.tail = np.zeros((2, self.length - 1))

    def process(self, x):
        """x: (BLOCK, 2) float -> (BLOCK, 2) float32."""
        xs = np.fft.rfft(x.T.astype(np.float64), self.size, axis=1)       # (in, bins)
        ys = np.einsum("oib,ib->ob", self.spectra, xs)
        y = np.fft.irfft(ys, self.size, axis=1)                          # (out, size)
        y[:, : self.length - 1] += self.tail
        out = y[:, : self.block]
        self.tail = y[:, self.block: self.block + self.length - 1].copy()
        return out.T.astype(np.float32)

    def flush(self):
        """What is left in the filter after the last block (length - 1 frames)."""
        out = self.tail.T.astype(np.float32)
        self.tail = np.zeros_like(self.tail)
        return out


def soft_limit(x, threshold: float = 0.92):
    """Leaves everything below `threshold` untouched and bends peaks towards 1.0 (no hard clipping)."""
    a = np.abs(x)
    over = a > threshold
    if not over.any():
        return x
    room = 1.0 - threshold
    y = x.copy()
    y[over] = np.sign(x[over]) * (threshold + room * np.tanh((a[over] - threshold) / room))
    return y


def replaygain_db(rms_dbfs: float, target: float = REPLAYGAIN_TARGET_DB, limit: float = 12.0) -> float:
    """Gain that brings a song of the measured RMS level (dBFS) to the target level, limited to +- `limit` dB."""
    if rms_dbfs is None or rms_dbfs != rms_dbfs or rms_dbfs <= -90.0:
        return 0.0
    return max(-limit, min(limit, target - rms_dbfs))


class Chain:
    """The whole chain for one stream: filtering by the matrix, ReplayGain, volume, limiter."""
    def __init__(self, cfg: DspConfig, fs: float, block: int = BLOCK):
        self.cfg, self.fs, self.block = cfg, fs, block
        matrix, self.delay = build_matrix(cfg, fs)
        self.convolver = Convolver(matrix, block) if matrix is not None else None
        self.gain_db = 0.0                    # ReplayGain of the song
        self.volume = 1.0                     # 0..1 amplitude

    def set_replaygain(self, gain_db: float) -> None:
        self.gain_db = gain_db if self.cfg.replaygain == "track" else 0.0

    def process(self, block):
        """block: (n, 2) float32 with n == self.block (the last one may be shorter: it is padded and cut again)."""
        n = len(block)
        if n < self.block:
            block = np.pad(block, ((0, self.block - n), (0, 0)))
        y = self.convolver.process(block) if self.convolver is not None else block
        gain = self.volume * db(self.gain_db)
        if gain != 1.0:
            y = y * np.float32(gain)
        if self.cfg.limiter:
            y = soft_limit(y)
        return np.ascontiguousarray(y[:n], dtype=np.float32)

    def flush(self):
        """The tail of the filter after the last block, with gain and limiter (empty without filtering)."""
        if self.convolver is None:
            return np.zeros((0, 2), dtype=np.float32)
        y = self.convolver.flush()
        gain = self.volume * db(self.gain_db)
        if gain != 1.0:
            y = y * np.float32(gain)
        return soft_limit(y) if self.cfg.limiter else y
