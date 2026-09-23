"""Time-slice band analysis: where the energy lives in time and frequency.

Splits each file into attack (0-15 ms) and body/tail (15 ms onward) and reports
band shares for each, so the tail rebuild can be aimed at the bands that the
recording itself keeps in its body rather than at its attack.
"""
from pathlib import Path
import wave
import struct
import math

import numpy as np

HERE = Path(__file__).resolve().parent
AKM = HERE.parent / 'AKMVideoAudio20260921' / 'S_AKM_Fire.wav'
BANDS = [(40, 80), (80, 160), (160, 315), (315, 630), (630, 1250),
         (1250, 2500), (2500, 5000), (5000, 10000)]


def load(path):
    with wave.open(str(path), 'rb') as handle:
        channels, width, rate = handle.getnchannels(), handle.getsampwidth(), handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    fmt = {1: 'b', 2: 'h', 4: 'i'}[width]
    values = np.array(struct.unpack('<%d%s' % (len(frames) // width, fmt), frames),
                      dtype=np.float64).reshape(-1, channels)
    return rate, values.mean(axis=1) / float(1 << (8 * width - 1))


def shares(signal, rate):
    spectrum = np.fft.rfft(signal * np.hanning(len(signal)))
    power = np.abs(spectrum) ** 2
    freqs = np.fft.rfftfreq(len(signal), 1.0 / rate)
    total = power.sum()
    return [(100 * power[(freqs >= low) & (freqs < high)].sum() / total) for low, high in BANDS]


for label, path in [("PKM raw source", HERE / 'S_PKM_Fire.raw.wav'),
                    ("AKM reference", AKM)]:
    rate, signal = load(path)
    nz = np.nonzero(signal != 0.0)[0]
    start = int(nz[0])
    body = start + int(rate * 0.015)
    attack = signal[start:body]
    rest = signal[body:nz[-1] + 1]
    print("%s: content %d..%d samples (%.1f ms)" %
          (label, nz[0], nz[-1], (nz[-1] - nz[0]) / rate * 1000))
    print("  attack 0-15 ms  shares:", " ".join("%.1f%%" % v for v in shares(attack, rate)))
    print("  body  15 ms+    shares:", " ".join("%.1f%%" % v for v in shares(rest, rate)))
    a_rms = math.sqrt(float(np.mean(attack ** 2)))
    b_rms = math.sqrt(float(np.mean(rest ** 2)))
    print("  attack rms=%.5f (%.1f dB)  body rms=%.5f (%.1f dB)  body/attack=%.1f dB"
          % (a_rms, 20 * math.log10(a_rms), b_rms, 20 * math.log10(b_rms),
             20 * math.log10(b_rms / a_rms)))
    print("  bands: " + " ".join("%d-%d" % b for b in BANDS))
    print()
