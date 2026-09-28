"""Find donor material that is genuinely clean once the authoring highpass is on.

The 2026-09-25 round chose its donor from a margin measured **without** the 80 Hz
highpass that the authoring chain actually applies (`../author_audio.py` line 34,
`../ChargeAudio35/author_audio.py` line 24).  Under the highpass the same window
loses most of the impact's low-frequency thump -- the bed barely changes, because
almost none of its energy is below 80 Hz -- so its margin collapses from
"100 % of frames >= 6 dB" to a minimum of -2.3 dB, with 96-139 ms sitting at
2.5-5.1 dB where the music is exposed.

This searches the whole decode, with the highpass applied, for the longest
contiguous runs that really stay >= 6 dB above the bed.
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
OWNED = 6.0

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
print(f'bed (80 Hz HP applied) = {bed_db:.1f} dB')

# frame the whole decode on the same grid the per-clip measurement uses
_, _, Z = stft(mono, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
               boundary='zeros', padded=True)
margin = 10 * np.log10(np.sum(np.abs(Z) ** 2, axis=0) + 1e-30) - bed_db
keep = margin >= OWNED

runs, i = [], 0
while i < len(keep):
    if keep[i]:
        j = i
        while j < len(keep) and keep[j]:
            j += 1
        runs.append((i, j))
        i = j
    else:
        i += 1
runs.sort(key=lambda r: r[1] - r[0], reverse=True)
print(f'\n{len(runs)} contiguous runs >= {OWNED} dB; longest first '
      f'(frame = {HOP / RATE * 1000:.1f} ms):')
CONTACTS = [('CoverOpen', 10.825, 11.340), ('BeltLift', 11.745, 12.185),
            ('BoxOut', 12.420, 12.900), ('BoxInsert', 14.245, 14.470),
            ('BeltSeat', 15.230, 15.435), ('CoverClose', 15.865, 16.100),
            ('ChargePullMove', 24.180, 24.710), ('ChargeRearStop', 24.710, 24.905),
            ('ChargePushMove', 24.905, 25.010), ('ChargeFrontStop', 25.010, 25.225)]
rows = []
for a, b in runs[:20]:
    t0, t1 = a * HOP / RATE, b * HOP / RATE
    inside = [n for n, ca, cb in CONTACTS if not (t1 <= ca or t0 >= cb)]
    rows.append({'start_s': round(t0, 3), 'end_s': round(t1, 3),
                 'run_ms': round((b - a) * HOP / RATE * 1000, 1),
                 'min_margin_db': round(float(margin[a:b].min()), 1),
                 'overlaps_contact': inside})
    print(' ', json.dumps(rows[-1]))

free = [r for r in rows if not r['overlaps_contact']]
print('\nlongest run that touches no processed contact:',
      json.dumps(free[0]) if free else 'NONE')

# per-contact clean head: how much of each clip's own head is genuinely clean
print('\nper-contact own-head clean run (with the highpass on):')
head_rows = []
for name, ca, cb in CONTACTS:
    i0, i1 = int(round(ca * RATE / HOP)), int(round(cb * RATE / HOP))
    m = margin[i0:i1 + 1]
    k = m >= OWNED
    # longest clean run inside this clip
    best, i = (0, 0), 0
    while i < len(k):
        if k[i]:
            j = i
            while j < len(k) and k[j]:
                j += 1
            if j - i > best[1] - best[0]:
                best = (i, j)
            i = j
        else:
            i += 1
    head_rows.append({'clip': name, 'clip_ms': round((cb - ca) * 1000, 1),
                      'clean_run_ms': [round(best[0] * HOP / RATE * 1000, 1),
                                       round(best[1] * HOP / RATE * 1000, 1)],
                      'clean_run_len_ms': round((best[1] - best[0]) * HOP / RATE * 1000, 1),
                      'min_margin_in_run_db': round(float(m[best[0]:best[1]].min()), 1)
                      if best[1] > best[0] else None})
    print(' ', json.dumps(head_rows[-1]))

(HERE / '_diag_donor_search.json').write_text(json.dumps(
    {'bed_db': bed_db, 'owned_db': OWNED, 'runs': rows, 'own_head': head_rows},
    indent=2), encoding='utf-8')