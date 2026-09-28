"""Diagnostic only: fixed transient gate vs spectral bed removal, head to head."""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.ndimage import uniform_filter1d
from scipy.signal import lfilter, stft, istft

HERE = Path(__file__).resolve().parent
RATE = 48000
x, rate = sf.read(HERE / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)
NP, HOP = 2048, 512
CLIPS = [('CoverOpen', 10.825, 11.340, .72), ('CoverClose', 15.865, 16.100, 1.)]


def expander(sig, thresh_db, ratio, max_gr_db, rel_ms=60.0):
    n = max(1, int(0.001 * RATE))
    env = np.sqrt(uniform_filter1d(sig ** 2, n, mode='nearest'))
    lvl_db = 20 * np.log10(env + 1e-12)
    gr_db = np.clip((thresh_db - lvl_db) * (ratio - 1.0), 0.0, max_gr_db)
    g_target = 10 ** (-gr_db / 20)
    # instant attack (follow the mechanism down), slow release (do not pump)
    a_rel = float(np.exp(-1.0 / (rel_ms * RATE / 1000)))
    out = lfilter([1 - a_rel], [1, -a_rel], g_target)
    out = np.minimum(out, g_target)      # never lag a downward gain change
    return sig * out, g_target


def spectral(sig, est, gamma, floor_db):
    f, t, Z = stft(sig, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    P = np.abs(Z) ** 2
    G = np.maximum(1.0 - gamma * est[:, None] / (P + 1e-20), 10 ** (floor_db / 10))
    G = uniform_filter1d(G, 3, axis=1, mode='nearest')
    y = np.asarray(istft(Z * G, fs=RATE, nperseg=NP, noverlap=NP - HOP,
                         window='hann', boundary=True)[1])[:len(sig)]
    return y


def bed_est(a, b, guard=1.0, pct=70):
    def P_of(s):
        _, _, Z = stft(s, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                       boundary='zeros', padded=True)
        return np.abs(Z) ** 2
    pre = mono[max(0, round((a - guard) * RATE)):round(a * RATE)]
    post = mono[round(b * RATE):round((b + guard) * RATE)]
    return np.percentile(np.concatenate([P_of(s) for s in (pre, post) if len(s) > NP],
                                        axis=1), pct, axis=1)


step = int(0.005 * RATE)
rows = []
for nm, a, b, tempo in CLIPS:
    seg = mono[round(a * RATE):round(b * RATE)].copy()
    prof = np.array([np.sqrt(np.mean(seg[i:i + step] ** 2))
                     for i in range(0, len(seg) - step, step)])
    ph = int(np.argmax(prof))
    tail = prof[ph:]
    tail_med_db = float(np.median(20 * np.log10(tail + 1e-12)))
    print(f'\n=== {nm}: peak hop {ph}, tail median {tail_med_db:.1f} dBFS')
    est = bed_est(a, b)
    cands = {'spectral_g3_f15': spectral(seg, est, 3.0, -15)}
    for th in (-34, -38, -42):
        for ratio in (2.0, 3.0):
            key = f'gate_t{th}_r{ratio}'
            cands[key], _ = expander(seg, th, ratio, 24.0)
    for key, y in cands.items():
        yprof = np.array([np.sqrt(np.mean(y[i:i + step] ** 2))
                          for i in range(0, len(y) - step, step)])
        d = 20 * np.log10((yprof + 1e-12) / (prof + 1e-12))
        rows.append({'clip': nm, 'method': key,
                     'overall_db': round(float(20 * np.log10(
                         np.sqrt(np.mean(y ** 2)) / np.sqrt(np.mean(seg ** 2)))), 3),
                     'tail_db_median': round(float(np.median(d[ph:])), 2),
                     'peak_db_change': round(float(d[ph]), 3),
                     'buildup_db_max': round(float(np.max(np.abs(d[:ph]))), 2) if ph > 0 else 0.0,
                     'first5_tail_db': [round(float(v), 1) for v in d[ph:ph + 5]],
                     'last10_tail_db': [round(float(v), 1) for v in d[-10:]]})
        print(json.dumps(rows[-1]))
    for key, y in cands.items():
        sf.write(HERE / f'_cand_{nm}_{key}.wav', y, RATE, subtype='PCM_16')
(HERE / '_diag_head2head.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')