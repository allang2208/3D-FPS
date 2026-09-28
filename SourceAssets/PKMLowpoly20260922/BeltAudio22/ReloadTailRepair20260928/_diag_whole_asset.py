"""Profile every delivered contact across its WHOLE length, in asset units.

The 2026-09-25 round and my 2026-09-28 round both only ever asked "where does the
contact stop masking the bed?" -- i.e. they looked at the tail, walking back from
the end.  Nobody profiled the *leading* part of a clip.

That is a hole, because each asset is a cut out of a continuous music bed: the
pre-impact lead-in is room tone plus music, with no mechanical content to mask
it.  `debgm_report.json` even recorded the number and I did not act on it --
`kept_head_min_margin_db` is 4.1 / 2.2 / 3.2 / 1.9 dB for BeltSeat, BeltLift,
ChargeRearStop and ChargePullMove, i.e. four of the five clips I "repaired"
still carry exposed music in the very region I kept bit-identical.

This reports, per contact, the masking margin over the entire asset so the
exposed spans -- head as well as tail -- are visible.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import stft

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
ROOT = PARENT.parent
RATE, NP, HOP = 48000, 2048, 512
OWNED, MUSIC = 6.0, 3.0

RELOAD = [
    ('CoverOpen', 10.825, 11.340), ('BeltLift', 11.745, 12.185),
    ('BoxOut', 12.420, 12.900), ('BoxInsert', 14.245, 14.470),
    ('BeltSeat', 15.230, 15.435), ('CoverClose', 15.865, 16.100),
]
CHARGE = [
    ('ChargePullMove', 24.180, 24.710), ('ChargeRearStop', 24.710, 24.905),
    ('ChargePushMove', 24.905, 25.010), ('ChargeFrontStop', 25.010, 25.225),
]
BED_WIN = {
    'reload': ([(1.10, 3.25), (3.90, 5.00), (6.10, 7.25), (7.65, 8.75), (9.05, 10.00)], -1.9473),
    'charge': ([(16.00, 16.50), (16.50, 17.00), (17.00, 17.50)], -0.22140514287644383),
}

# the delivered (repaired) WAVs, which is what the user actually hears
REPAIRED = {}
for row in json.loads((PARENT / 'tail_repair_manifest.json').read_text(encoding='utf-8'))['repairs']:
    REPAIRED[row['asset_name']] = PARENT / row['wav']

x, _ = sf.read(PARENT / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)


def bed_db(group):
    wins, _ = BED_WIN[group]
    Ps = []
    for a, b in wins:
        _, _, Z = stft(mono[round(a * RATE):round(b * RATE)], fs=RATE, nperseg=NP,
                       noverlap=NP - HOP, window='hann', boundary='zeros', padded=True)
        Ps.append(np.abs(Z) ** 2)
    return float(10 * np.log10(np.sum(np.percentile(np.concatenate(Ps, axis=1), 70, axis=1)) + 1e-30))


def frames_db(sig):
    _, _, Z = stft(sig, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    return 10 * np.log10(np.sum(np.abs(Z) ** 2, axis=0) + 1e-30)


def spans(mask):
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]:
                j += 1
            out.append((round(i * HOP / RATE * 1000, 1), round((j - 1) * HOP / RATE * 1000, 1)))
            i = j
        else:
            i += 1
    return out


rows = []
for group, items in (('reload', RELOAD), ('charge', CHARGE)):
    bed_src = bed_db(group)
    bed_asset = bed_src + BED_WIN[group][1]
    for name, a, b in items:
        path = REPAIRED.get('S_PKM_%s' % name) or (PARENT / f'S_PKM_{name}.wav')
        sig = np.asarray(sf.read(path)[0], dtype=np.float64)
        m = frames_db(sig) - bed_asset
        owned = m >= OWNED
        first_owned = int(np.argmax(owned)) if owned.any() else -1
        row = {
            'clip': name, 'asset_ms': round(len(sig) / RATE * 1000, 1),
            'source': 'repaired' if 'S_PKM_%s' % name in REPAIRED else 'raw cut',
            'bed_asset_db': round(bed_asset, 1),
            'frames': len(m),
            'min_margin_db': round(float(m.min()), 1),
            'pct_owned': round(100 * float(owned.mean()), 1),
            'pct_music': round(100 * float((m < MUSIC).mean()), 1),
            'head_exposed_ms': round(first_owned * HOP / RATE * 1000, 1) if first_owned > 0 else 0.0,
            'leading_spans': spans(~owned[:first_owned]) if first_owned > 0 else [],
            'trailing_spans': spans(~owned[first_owned:]) if first_owned >= 0 else [],
        }
        row['trailing_spans'] = [(round(a2 + first_owned * HOP / RATE * 1000, 1), b2)
                                 for a2, b2 in row['trailing_spans']]
        rows.append(row)
        print(json.dumps(row))

(HERE / '_diag_whole_asset.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print('\n--- summary: music-exposed time per clip (asset units, 6 dB rule) ---')
for r in rows:
    print('  %-16s %6.1f ms   owned %5.1f%%   music(<3dB) %5.1f%%   head exposed %6.1f ms   %s'
          % (r['clip'], r['asset_ms'], r['pct_owned'], r['pct_music'],
             r['head_exposed_ms'], r['source']))