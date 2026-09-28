"""How clean can donor material actually get, with the authoring highpass applied?

`_diag_donor_search.py` shows the best *long* clean run in the whole decode is
only 6.0 dB above the bed.  A rebuild can therefore never suppress the music by
more than the donor's own margin: donor = contact + bed, so a margin of M dB
means the music is M dB below the replaced region's level.  6 dB is not removal.

This looks for shorter but much better-masked runs instead, which can be
mirrored (not tiled, so no click) to reach any tail length.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt, stft

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
RATE = 48000
NP, HOP = 2048, 512

x, _ = sf.read(PARENT / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)
mono = sosfiltfilt(butter(2, 80, fs=RATE, btype='highpass', output='sos'), mono)

BED_WIN = [(1.10, 3.25), (3.90, 5.00), (6.10, 7.25), (7.65, 8.75), (9.05, 10.00)]
Ps = []
for a, b in BED_WIN:
    _, _, Z = stft(mono[round(a * RATE):round(b * RATE)], fs=RATE, nperseg=NP,
                   noverlap=NP - HOP, window='hann', boundary='zeros', padded=True)
    Ps.append(np.abs(Z) ** 2)
bed_db = float(10 * np.log10(np.sum(np.percentile(np.concatenate(Ps, axis=1), 70, axis=1)) + 1e-30))

_, _, Z = stft(mono, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
               boundary='zeros', padded=True)
margin = 10 * np.log10(np.sum(np.abs(Z) ** 2, axis=0) + 1e-30) - bed_db
print(f'bed = {bed_db:.1f} dB (80 Hz HP applied)')

rows = []
for thr in (6, 8, 10, 12, 14, 16, 18, 20):
    keep = margin >= thr
    best, i = (0, 0), 0
    while i < len(keep):
        if keep[i]:
            j = i
            while j < len(keep) and keep[j]:
                j += 1
            if j - i > best[1] - best[0]:
                best = (i, j)
            i = j
        else:
            i += 1
    a, b = best
    seg = None if b <= a else {
        'threshold_db': thr,
        'start_s': round(a * HOP / RATE, 3), 'end_s': round(b * HOP / RATE, 3),
        'run_ms': round((b - a) * HOP / RATE * 1000, 1),
        'min_margin_db': round(float(margin[a:b].min()), 1),
        'mean_margin_db': round(float(margin[a:b].mean()), 1),
    }
    if seg:
        rows.append(seg)
        print(' ', json.dumps(seg))

# the strongest sustained stretch overall: maximise (min margin) over >= 120 ms
win = round(0.120 * RATE / HOP)
best = None
for i in range(0, len(margin) - win):
    m = float(margin[i:i + win].min())
    if best is None or m > best[0]:
        best = (m, i)
m, i = best
peak = {'window_ms': 120, 'start_s': round(i * HOP / RATE, 3),
        'end_s': round((i + win) * HOP / RATE, 3),
        'min_margin_db': round(m, 1),
        'mean_margin_db': round(float(margin[i:i + win].mean()), 1)}
print('\nbest 120 ms window in the whole decode:', json.dumps(peak))

(HERE / '_diag_donor_thresholds.json').write_text(json.dumps(
    {'bed_db': bed_db, 'by_threshold': rows, 'best_120ms': peak}, indent=2), encoding='utf-8')