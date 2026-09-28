"""Exactly which milliseconds of each delivered asset are unmasked music?

The margin profile is the right question but the earlier reports buried it:
`_diag_whole_asset.py` reported nonsense spans like [149.4, 149.3], and the
`padded=True` STFT adds a zero-padded first and last frame that always reads as
maximally exposed.  This trims those, uses the full band, and prints the leading
and trailing exposed runs in milliseconds so it is obvious how much of each cue
still carries audible bed.

Also re-checks ChargePushMove, which `_author_debgm.py` skipped with
"trailing region is digital silence" while quoting a handover of 245.3 ms for a
105 ms asset -- an impossible number, so that skip reason was never valid.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import stft

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
ROOT = PARENT.parent
RATE, NP, HOP = 48000, 1024, 256
OWNED, MUSIC = 6.0, 3.0

RELOAD = [('CoverOpen', 10.825, 11.340), ('BeltLift', 11.745, 12.185),
          ('BoxOut', 12.420, 12.900), ('BoxInsert', 14.245, 14.470),
          ('BeltSeat', 15.230, 15.435), ('CoverClose', 15.865, 16.100)]
CHARGE = [('ChargePullMove', 24.180, 24.710), ('ChargeRearStop', 24.710, 24.905),
          ('ChargePushMove', 24.905, 25.010), ('ChargeFrontStop', 25.010, 25.225)]
BED_WIN = {'reload': [(1.10, 3.25), (3.90, 5.00), (6.10, 7.25), (7.65, 8.75), (9.05, 10.00)],
           'charge': [(16.00, 16.50), (16.50, 17.00), (17.00, 17.50)]}

x, _ = sf.read(PARENT / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)


def spec(sig):
    _, _, Z = stft(sig, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    return np.abs(Z) ** 2


bed = {g: float(np.mean([spec(mono[round(a * RATE):round(b * RATE)]).mean(axis=1).sum()
                         for a, b in w])) for g, w in BED_WIN.items()}

repaired = {r['asset_name']: PARENT / r['wav'] for r in json.loads(
    (PARENT / 'tail_repair_manifest.json').read_text(encoding='utf-8'))['repairs']}


def path_for(group, name):
    return repaired.get('S_PKM_%s' % name) or (
        (PARENT / f'S_PKM_{name}.wav') if group == 'reload'
        else (ROOT / 'ChargeAudio35' / f'S_PKM_{name}.wav'))


def runs(mask, off_ms):
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]:
                j += 1
            out.append((round(off_ms + i * HOP / RATE * 1000, 1),
                        round(off_ms + (j - 1) * HOP / RATE * 1000, 1)))
            i = j
        else:
            i += 1
    return out


rows = []
print('%-16s %7s %7s %8s  %-26s %s' % ('clip', 'asset', 'peakdB', 'music%', 'leading exposed', 'trailing exposed'))
for group, items in (('reload', RELOAD), ('charge', CHARGE)):
    for name, a, b in items:
        p = path_for(group, name)
        sig = np.asarray(sf.read(p)[0], dtype=np.float64)
        P = spec(sig).sum(axis=0)[1:-1]                     # drop padded edge frames
        m = 10 * np.log10(P / (bed[group] + 1e-30) + 1e-30)
        owned = m >= OWNED
        first = int(np.argmax(owned)) if owned.any() else 0
        lead = runs(~owned[:first], 0.0) if first > 0 else []
        trail = runs(~owned[first:], first * HOP / RATE * 1000) if owned.any() else []
        row = {'clip': name, 'asset': 'repaired' if 'S_PKM_%s' % name in repaired else 'raw',
               'asset_ms': round(len(sig) / RATE * 1000, 1),
               'peak_dbfs': round(20 * np.log10(float(np.max(np.abs(sig))) + 1e-30), 1),
               'pct_music_frames': round(100 * float((m < MUSIC).mean()), 1),
               'first_owned_ms': round(first * HOP / RATE * 1000, 1),
               'leading_exposed': lead, 'trailing_exposed': trail,
               'leading_ms': round(sum(b2 - a2 for a2, b2 in lead) + 0.0, 1),
               'trailing_ms': round(sum(b2 - a2 for a2, b2 in trail) + 0.0, 1)}
        rows.append(row)
        print('%-16s %6.1f %7.1f %7.1f%%  %-26s %s'
              % (name, row['asset_ms'], row['peak_dbfs'], row['pct_music_frames'],
                 ('%s (%d spans, %.0f ms)' % (lead[0], len(lead), row['leading_ms'])) if lead else 'none',
                 ('%s (%d spans, %.0f ms)' % (trail[0], len(trail), row['trailing_ms'])) if trail else 'none'))

(HERE / '_diag_exposed_spans.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print('\n=== ChargePushMove, which was skipped on an impossible reason ===')
row = next(r for r in rows if r['clip'] == 'ChargePushMove')
print(json.dumps(row, indent=2))