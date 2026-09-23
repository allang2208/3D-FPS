"""Sweep EQ strength, tail gain and tail length; score each candidate.

The first EQ attempt overshot badly (energy went from 18.9% low / 55% upper-mid to
86% low / 5.6% upper-mid), so the remaining choice is made by measurement instead
of by hand. Each candidate is scored on how close it lands to a *moderate* subset
of the AKM's spectral move - halfway toward the reference, keeping the PKM's own
character - plus crest factor and the level still ringing at the fire interval.

Writes candidates to a scratch folder; does not touch S_PKM_Fire.wav.
"""
from pathlib import Path
import wave
import struct
import math

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, sosfiltfilt

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'S_PKM_Fire.raw.wav'
SCRATCH = HERE / 'tone-candidates'
SCRATCH.mkdir(exist_ok=True)
AKM = HERE.parent / 'AKMVideoAudio20260921' / 'S_AKM_Fire.wav'

FIRE_INTERVAL = 0.092308
REFERENCE_PEAK = 0.6025
BANDS = [(40, 80), (80, 160), (160, 315), (315, 630), (630, 1250),
         (1250, 2500), (2500, 5000), (5000, 10000), (10000, 18000)]

x, rate = sf.read(SOURCE, always_2d=True, dtype='float64')
signal = x[:, 0]
nonzero = np.nonzero(signal != 0.0)[0]
content_start, content_end = int(nonzero[0]), int(nonzero[-1]) + 1
trimmed = signal[max(0, content_start - int(0.0005 * rate)):content_end].copy()


def biquad(kind, freq, gain_db, q, sample_rate):
    a = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * freq / sample_rate
    cw, sw = math.cos(w0), math.sin(w0)
    if kind == 'peak':
        alpha = sw / (2.0 * q)
        b = [1 + alpha * a, -2 * cw, 1 - alpha * a]
        d = [1 + alpha / a, -2 * cw, 1 - alpha / a]
    else:
        alpha = sw / 2.0 * math.sqrt((a + 1 / a) * (1 / q - 1) + 2)
        sq = 2.0 * math.sqrt(a) * alpha
        if kind == 'lowshelf':
            b = [a * ((a + 1) - (a - 1) * cw + sq), 2 * a * ((a - 1) - (a + 1) * cw),
                 a * ((a + 1) - (a - 1) * cw - sq)]
            d = [(a + 1) + (a - 1) * cw + sq, -2 * ((a - 1) + (a + 1) * cw),
                 (a + 1) + (a - 1) * cw - sq]
        else:
            b = [a * ((a + 1) + (a - 1) * cw + sq), -2 * a * ((a - 1) + (a + 1) * cw),
                 a * ((a + 1) + (a - 1) * cw - sq)]
            d = [(a + 1) - (a - 1) * cw + sq, 2 * ((a - 1) - (a + 1) * cw),
                 (a + 1) - (a - 1) * cw - sq]
    return np.array([[b[0] / d[0], b[1] / d[0], b[2] / d[0], 1.0, d[1] / d[0], d[2] / d[0]]])


def eq_curve(scale):
    # Moves a fraction of the way from the PKM's tilt toward the AKM's. The
    # 40-80 Hz band is left alone: it is room rumble in the reference, not gun.
    return [('lowshelf', 90.0, -2.0 * scale, 0.7),
            ('lowshelf', 200.0, 3.0 * scale, 0.7),
            ('peak', 500.0, 1.5 * scale, 0.9),
            ('peak', 900.0, -2.0 * scale, 0.9),
            ('peak', 2400.0, -1.5 * scale, 1.0),
            ('highshelf', 7000.0, -2.0 * scale, 0.707)]


def apply_eq(sig, curve):
    out = sig
    for kind, freq, gain, quality in curve:
        if abs(gain) > 1e-6:
            out = sosfilt(biquad(kind, freq, gain, quality, rate), out)
    return out


TAIL_TEMPLATE = ((50.0, 200.0, 0.110), (200.0, 800.0, 0.070),
                 (800.0, 3500.0, 0.032), (3500.0, 9000.0, 0.016))


def build(eq_scale, tail_gain, length_s):
    curve = eq_curve(eq_scale)
    tilted = apply_eq(signal, curve)
    attack = apply_eq(trimmed, curve)
    total = int(length_s * rate)
    tail_length = total - len(attack)
    if tail_length <= 0:
        return None
    src = max(0, content_start - int(0.0005 * rate))
    dt = np.arange(tail_length) / rate
    tail = np.zeros(tail_length)
    for low, high, tau in TAIL_TEMPLATE:
        band = sosfiltfilt(butter(2, [low, high], btype='bandpass', fs=rate, output='sos'), tilted)
        tail += band[src:src + tail_length] * np.exp(-dt / tau)
    tail *= tail_gain
    probe = max(1, int(0.005 * rate))
    ar = math.sqrt(float(np.mean(attack[-probe:] ** 2)))
    tr = math.sqrt(float(np.mean(tail[:probe] ** 2)))
    if tr > 0:
        tail *= ar / tr
    # Gain applies after the splice match, so the control actually reaches the
    # tail's absolute level instead of being cancelled by the match.
    tail *= tail_gain
    y = np.concatenate([attack, tail])
    blend = min(int(0.012 * rate), len(attack) // 2, tail_length // 2)
    ramp = np.linspace(0.0, 1.0, blend)
    y[len(attack) - blend:len(attack)] *= 1.0 - ramp * 0.5
    y[len(attack):len(attack) + blend] *= 0.5 + ramp * 0.5
    duck = int(0.035 * rate)
    y[duck:] *= 0.90
    y *= REFERENCE_PEAK / np.max(np.abs(y))
    fade = int(0.008 * rate)
    y[-fade:] *= np.linspace(1.0, 0.0, fade)
    return y


def shares(sig):
    spectrum = np.fft.rfft(sig * np.hanning(len(sig)))
    power = np.abs(spectrum) ** 2
    freqs = np.fft.rfftfreq(len(sig), 1.0 / rate)
    total = power.sum()
    return np.array([power[(freqs >= lo) & (freqs < hi)].sum() / total for lo, hi in BANDS])


def measure(y):
    peak = float(np.max(np.abs(y)))
    rms = math.sqrt(float(np.mean(y ** 2)))
    sh = shares(y)
    win = int(rate * 0.010)
    env = [math.sqrt(float(np.mean(y[i:i + win] ** 2))) for i in range(0, len(y) - win, win)]
    at_next = int(FIRE_INTERVAL / 0.010)
    gap_peak = max(env) if env else 0
    silent = max([sum(1 for i in range(k, min(k + 4, len(env))) if env[i] < gap_peak * 0.01)
                  for k in range(len(env))] or [0])
    return dict(peak=peak, rms=rms, crest=20 * math.log10(peak / rms), shares=sh,
                at_next=20 * math.log10(max(env[at_next], 1e-9)) if at_next < len(env) else -180,
                env=env)


# Reference shares straight from the accepted AKM.
with wave.open(str(AKM), 'rb') as handle:
    akm_rate = handle.getframerate()
    akm_frames = handle.readframes(handle.getnframes())
akm_vals = np.array(struct.unpack('<%dh' % (len(akm_frames) // 2), akm_frames),
                    dtype=np.float64).reshape(-1, 2).mean(axis=1) / 32768.0
akm_shares = shares(akm_vals)
base_shares = shares(trimmed)
# Halfway-toward-reference target: keep half of the PKM's own character.
target = base_shares + 0.5 * (akm_shares - base_shares)
print("target band shares (halfway to AKM):")
print("  " + " ".join("%d-%d:%.1f%%" % (lo, hi, t * 100) for (lo, hi), t in zip(BANDS, target)))
print()

rows = []
print("%-22s %6s %6s %8s %8s" % ("candidate", "crest", "rms", "@92ms", "tilt err"))
for eq_scale in (0.3, 0.45, 0.6, 0.8):
    for tail_gain in (0.20, 0.35, 0.50):
        for length_s in (0.130, 0.150):
            y = build(eq_scale, tail_gain, length_s)
            if y is None:
                continue
            m = measure(y)
            err = float(np.abs(m['shares'] - target).sum()) * 100
            name = "eq%.2f_g%.2f_l%03d" % (eq_scale, tail_gain, int(length_s * 1000))
            sf.write(SCRATCH / (name + '.wav'), y, rate, subtype='PCM_16')
            rows.append((err, name, m, y))
            print("%-22s %6.1f %6.4f %8.1f %8.1f" % (name, m['crest'], m['rms'], m['at_next'], err))

rows.sort(key=lambda r: r[0])
print()
for err, name, m, y in rows[:4]:
    print("%s  tilt_err=%.1f  crest=%.1f dB  shares: %s" %
          (name, err, m['crest'], " ".join("%.1f" % (v * 100) for v in m['shares'])))
print()
print("AKM shares for reference: " + " ".join("%.1f" % (v * 100) for v in akm_shares))
print("PKM raw shares          : " + " ".join("%.1f" % (v * 100) for v in base_shares))
print("target (halfway)        : " + " ".join("%.1f" % (v * 100) for v in target))
