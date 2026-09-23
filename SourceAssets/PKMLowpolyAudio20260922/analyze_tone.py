"""Measure the PKM fire one-shot against the accepted AKM reference.

No listening is available, so the diagnosis has to be numeric: band energies,
spectral tilt, crest factor, and the blast-to-tail balance. Everything measured
here drives the EQ/space decisions in author_audio.py.
"""
from pathlib import Path
import wave
import struct
import math

import numpy as np

HERE = Path(__file__).resolve().parent
AKM = HERE.parent / 'AKMVideoAudio20260921' / 'S_AKM_Fire.wav'

# Octave-ish bands used for the tonal comparison, in Hz.
BANDS = [(40, 80), (80, 160), (160, 315), (315, 630), (630, 1250),
         (1250, 2500), (2500, 5000), (5000, 10000), (10000, 18000)]


def load_mono(path):
    with wave.open(str(path), 'rb') as handle:
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        rate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    fmt = {1: 'b', 2: 'h', 4: 'i'}[width]
    scale = float(1 << (8 * width - 1))
    values = np.array(struct.unpack('<%d%s' % (len(frames) // width, fmt), frames), dtype=np.float64)
    values = values.reshape(-1, channels) / scale
    return rate, values.mean(axis=1), channels


def band_energies(signal, rate):
    """Fraction of total energy per band, plus absolute dBFS level per band."""
    spectrum = np.fft.rfft(signal * np.hanning(len(signal)))
    power = np.abs(spectrum) ** 2
    freqs = np.fft.rfftfreq(len(signal), 1.0 / rate)
    total = power.sum()
    out = []
    for low, high in BANDS:
        mask = (freqs >= low) & (freqs < high)
        energy = power[mask].sum()
        out.append((low, high, energy / total if total else 0.0,
                    10 * math.log10(max(energy / max(1, mask.sum()), 1e-20))))
    return out


def report(label, path):
    rate, signal, channels = load_mono(path)
    duration = len(signal) / rate
    peak = float(np.max(np.abs(signal)))
    rms = math.sqrt(float(np.mean(signal ** 2)))
    crest = 20 * math.log10(peak / rms) if rms > 0 else 0.0
    # Where the energy actually sits in time.
    win = int(rate * 0.010)
    env = np.array([math.sqrt(float(np.mean(signal[i:i + win] ** 2)))
                    for i in range(0, len(signal) - win, win)])
    peak_index = int(np.argmax(env))
    half = next((i for i in range(peak_index, len(env)) if env[i] <= env[peak_index] * 0.5),
                len(env) - 1)
    print("%s  ch=%d sr=%d dur=%.4fs peak=%.4f rms=%.5f crest=%.1f dB" %
          (label, channels, rate, duration, peak, rms, crest))
    print("   energy centroid in time: peak at %.1f ms, -6 dB at %.1f ms" %
          (peak_index * 10.0, half * 10.0))
    bars = band_energies(signal, rate)
    print("   band share / level:")
    for low, high, share, level in bars:
        print("     %6d-%-6d %6.2f%%  %7.1f dB   %s" %
              (low, high, share * 100, level, '#' * int(round(share * 200))))
    return bars


print("=" * 78)
pkm = report("PKM (current authored)", HERE / 'S_PKM_Fire.wav')
print()
akm = report("AKM (accepted reference)", AKM)
print("=" * 78)
print("Band share difference (PKM - AKM), positive = PKM has more there:")
for (low, high, pshare, _), (_, _, ashare, _) in zip(pkm, akm):
    delta = (pshare - ashare) * 100
    verdict = ""
    if delta <= -3.0:
        verdict = "  <-- PKM deficient"
    elif delta >= 3.0:
        verdict = "  <-- PKM excessive"
    print("  %6d-%-6d  %+6.2f pp%s" % (low, high, delta, verdict))
