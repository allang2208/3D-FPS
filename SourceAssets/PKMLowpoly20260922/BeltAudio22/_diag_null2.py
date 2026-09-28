"""Diagnostic only: honest null test on genuinely quiet windows.

Scans the whole decode for stretches whose level really is bed-only, then
applies a locally-estimated mask to a *different* quiet stretch and reports the
actual null depth.  No silence is assumed from the earlier RMS scan.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import stft, istft

HERE = Path(__file__).resolve().parent
RATE = 48000
x, rate = sf.read(HERE / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)
NP, HOP = 2048, 512
dur = len(mono) / RATE


def env(step_s=0.05):
    n = int(step_s * RATE)
    e = np.sqrt(np.convolve(mono ** 2, np.ones(n) / n, mode='same'))[::n]
    return e, step_s


e, step = env()
gd = float(np.percentile(e, 20))
print(f'file {dur:.2f}s, envelope 20th pct = {gd:.5f}, median = {np.median(e):.5f}')

# quiet windows: 0.35 s whose envelope never exceeds 1.6x the 20th percentile
q = e < gd * 1.6
win = int(0.35 / step)
cand = []
i = 0
while i < len(q) - win:
    if q[i:i + win].all():
        j = i
        while j < len(q) and q[j]:
            j += 1
        cand.append((round(i * step, 2), round(j * step, 2), round(float(e[i:j].max()), 5)))
        i = j
    else:
        i += 1
print('quiet stretches (start, end, max_env):')
for c in cand:
    print('  ', c)
(HERE / '_diag_quiet.json').write_text(json.dumps(cand, indent=2), encoding='utf-8')


def est_from(a, b):
    seg = mono[round(a * RATE):round(b * RATE)]
    f, t, Z = stft(seg, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    return np.median(np.abs(Z) ** 2, axis=1)


def apply_mask(seg, est, gamma=2.0, floor_db=-18):
    f, t, Z = stft(seg, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    P = np.abs(Z) ** 2
    G = np.maximum(1.0 - gamma * est[:, None] / (P + 1e-20), 10 ** (floor_db / 10))
    y = istft(Z * G, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
              boundary=True)[1]
    return np.asarray(y)[:len(seg)], float(np.mean(G))


def rms(v):
    return float(np.sqrt(np.mean(v ** 2)))


# null test: for each pair of quiet stretches >=1 s apart, estimate from one, null other
print('\nnull tests (estimate window -> target window):')
rows = []
for i in range(len(cand)):
    for j in range(len(cand)):
        if i == j:
            continue
        a1, b1, _ = cand[i]
        a2, b2, _ = cand[j]
        if b1 - a1 < 0.4 or b2 - a2 < 0.4:
            continue
        if abs(a2 - a1) < 1.0:
            continue
        est = est_from(a1, b1)
        tgt = mono[round(a2 * RATE):round(b2 * RATE)]
        y, gm = apply_mask(tgt, est)
        rows.append({'est': [a1, b1], 'target': [a2, b2],
                     'before_rms': round(rms(tgt), 6), 'after_rms': round(rms(y), 6),
                     'reduction_db': round(20 * np.log10(rms(y) / rms(tgt)), 2),
                     'mean_gain': round(gm, 3)})
        print('  ', json.dumps(rows[-1]))
        if len(rows) > 24:
            break
    if len(rows) > 24:
        break
(HERE / '_diag_null2.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')