"""Build the rebuild listening pack: A/B/C for the two clips, loudness matched."""
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
OUT = HERE / 'rebuild' / '_listening'
OUT.mkdir(parents=True, exist_ok=True)
RATE = 48000


def norm(y, target_dbfs=-6.0):
    p = float(np.max(np.abs(y))) or 1.0
    return y * (10 ** (target_dbfs / 20) / p)


def rms_db(v):
    return round(float(20 * np.log10(np.sqrt(np.mean(np.asarray(v) ** 2)) + 1e-12)), 2)


rows = []
for name in ('CoverOpen', 'CoverClose'):
    o, _ = sf.read(HERE / f'S_PKM_{name}.wav')
    n, _ = sf.read(HERE / f'rebuild/S_PKM_{name}_rebuilt_delivered.wav')
    ot, _ = sf.read(HERE / f'rebuild/_{name}_removed_tail.wav')
    nt, _ = sf.read(HERE / f'rebuild/_{name}_new_tail.wav')
    o, n = np.asarray(o), np.asarray(n)
    L = min(len(o), len(n))
    o, n = o[:L], n[:L]
    # full one-shots, short loop so they can be compared back to back
    sf.write(OUT / f'1_{name}_BEFORE.wav', np.tile(norm(o), 3), RATE, subtype='PCM_16')
    sf.write(OUT / f'2_{name}_AFTER.wav', np.tile(norm(n), 3), RATE, subtype='PCM_16')
    sf.write(OUT / f'3_{name}_difference.wav', np.tile(norm(o - n), 5), RATE, subtype='PCM_16')
    # the contaminated tail alone, then the rebuilt tail alone (normalised)
    sf.write(OUT / f'4_{name}_tail_OLD_contaminated.wav', np.tile(norm(ot), 6), RATE,
             subtype='PCM_16')
    sf.write(OUT / f'5_{name}_tail_NEW_rebuilt.wav', np.tile(norm(nt), 6), RATE,
             subtype='PCM_16')
    rows.append({'clip': name, 'len': L,
                 'before_rms_dbfs': rms_db(o), 'after_rms_dbfs': rms_db(n),
                 'old_tail_rms_dbfs': rms_db(ot), 'new_tail_rms_dbfs': rms_db(nt),
                 'difference_rms_dbfs': rms_db(o - n),
                 'difference_over_signal_db': round(rms_db(o - n) - rms_db(o), 1),
                 'adjusted_for_length': len(sf.read(HERE / f'S_PKM_{name}.wav')[0]) != L})
    print(rows[-1])
print('\nfiles:')
for p in sorted(OUT.glob('*.wav')):
    print(' ', p.name)