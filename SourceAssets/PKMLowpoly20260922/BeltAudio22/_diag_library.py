"""Diagnostic only: build the clean-material library for tail rebuild.

For every contact in the reference video, finds the time range where the
mechanism dominates the local bed by >= 6 dB.  Only those ranges are free of
audible background music and can donate rebuild material.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import stft

HERE = Path(__file__).resolve().parent
RATE = 48000
NP, HOP = 2048, 512
x, rate = sf.read(HERE / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)

BED_WIN = [(1.10, 3.25), (3.90, 5.00), (6.10, 7.25), (7.65, 8.75), (9.05, 10.00)]
CONTACTS = [('CoverOpen', 10.825, 11.340), ('BeltLift', 11.745, 12.185),
            ('BoxOut', 12.420, 12.900), ('BoxInsert', 14.245, 14.470),
            ('BeltSeat', 15.230, 15.435), ('CoverClose', 15.865, 16.100),
            ('ChargePull', 24.710, 24.935), ('ChargeRelease', 25.010, 25.215)]


def P_of(seg):
    _, _, Z = stft(seg, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    return np.abs(Z) ** 2


Ps = []
for lo, hi in BED_WIN:
    Ps.append(P_of(mono[round(lo * RATE):round(hi * RATE)]))
bed = np.percentile(np.concatenate(Ps, axis=1), 70, axis=1)
bed_db = 10 * np.log10(np.sum(bed) + 1e-30)
print(f'bed total {bed_db:.1f} dB (reference)')

rows = []
for name, a, b in CONTACTS:
    seg = mono[round(a * RATE):round(b * RATE)]
    _, _, Z = stft(seg, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    P = np.abs(Z) ** 2
    fr = 10 * np.log10(np.sum(P, axis=0) + 1e-30)
    margin = fr - bed_db
    ok = margin >= 6.0
    # longest contiguous run of ok
    best = (0, 0)
    i = 0
    while i < len(ok):
        if ok[i]:
            j = i
            while j < len(ok) and ok[j]:
                j += 1
            if j - i > best[1] - best[0]:
                best = (i, j)
            i = j
        else:
            i += 1
    i0, i1 = best
    rows.append({'name': name, 'window': [a, b], 'clip_ms': round(len(seg) / RATE * 1000, 1),
                 'clean_run_ms': [round(i0 * HOP / RATE * 1000, 1),
                                  round(i1 * HOP / RATE * 1000, 1)],
                 'clean_run_len_ms': round((i1 - i0) * HOP / RATE * 1000, 1),
                 'max_margin_db': round(float(margin.max()), 1),
                 'pct_frames_clean': round(100 * float(ok.mean()), 1)})
    print(json.dumps(rows[-1]))
(HERE / '_diag_library.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')