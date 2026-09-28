"""Diagnostic only: envelope map with bed floor, and stronger-mask convergence."""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.ndimage import uniform_filter1d
from scipy.signal import stft, istft

HERE = Path(__file__).resolve().parent
RATE = 48000
x, rate = sf.read(HERE / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)
NP, HOP = 2048, 512

# ---- 1. envelope map: every 0.25 s, level and its 120-600 Hz share --------
step = int(0.25 * RATE)
print('t(s)   rms_dBFS  60-260Hz_dBFS  260-600Hz_dBFS  note')
for i in range(0, len(mono) - step, step):
    s = mono[i:i + step]
    f, t, Z = stft(s, fs=RATE, nperseg=1024, noverlap=512, window='hann')
    P = np.mean(np.abs(Z) ** 2, axis=1)
    def bdb(lo, hi):
        m = (f >= lo) & (f < hi)
        return 10 * np.log10(np.mean(P[m]) + 1e-30)
    r = 20 * np.log10(np.sqrt(np.mean(s ** 2)) + 1e-12)
    print(f'{i/RATE:6.2f} {r:9.1f} {bdb(60,260):14.1f} {bdb(260,600):15.1f}')

# ---- 2. does a stronger mask help?  convergence on the exposed tail -------
def P_of(seg):
    _, _, Z = stft(seg, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    return np.abs(Z) ** 2


def mask(sig, est, gamma, floor_db):
    f, t, Z = stft(sig, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    P = np.abs(Z) ** 2
    G = np.maximum(1.0 - gamma * est[:, None] / (P + 1e-20), 10 ** (floor_db / 10))
    G = uniform_filter1d(G, 3, axis=1, mode='nearest')
    return np.asarray(istft(Z * G, fs=RATE, nperseg=NP, noverlap=NP - HOP,
                            window='hann', boundary=True)[1])[:len(sig)], float(G.mean())


print('\ngamma convergence (median gain, overall dB, tail-share of harmonic energy):')
F0 = 117.2
for nm, a, b in [('CoverOpen', 10.825, 11.340), ('CoverClose', 15.865, 16.100)]:
    seg = mono[round(a * RATE):round(b * RATE)]
    pre = mono[max(0, round((a - 1.0) * RATE)):round(a * RATE)]
    post = mono[round(b * RATE):round((b + 1.0) * RATE)]
    est = np.percentile(np.concatenate([P_of(pre), P_of(post)], axis=1), 70, axis=1)
    for gamma in (3, 6, 10, 20, 50):
        y, gm = mask(seg, est, gamma, -12)
        print(f'  {nm} gamma={gamma:3d} mean_gain={gm:.3f} '
              f'overall_db={20*np.log10(np.sqrt(np.mean(y**2))/np.sqrt(np.mean(seg**2))):+.2f}')