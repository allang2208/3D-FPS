"""Diagnostic only: is the Close tail mechanism or wind?

If the tail is essentially all wind, no donor colour-matching is needed -- the
honest rebuild is a smooth natural decay, not a spectral imitation.  This
compares the tail's energy against the wind-only stretches of the same
recording, in the same bands, so the two can be told apart.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

HERE = Path(__file__).resolve().parent
OUT = HERE / '_wind'
SR = 48000
NPERSEG, NOVERLAP = 2048, 1792
BANDS = [(200, 400), (400, 800), (800, 1600), (1600, 3200), (3200, 6400), (6400, 12000)]

clean, sr = sf.read(HERE / 'Cleaned/715-reloading-wind-reduced.wav', always_2d=True)
raw, _ = sf.read(HERE / 'Analysis/715-reloading-decoded.wav', always_2d=True)

# the delivered Close tail, and an equal-length piece of pure wind nearby
TAIL = (5.320, 5.420)
WIND = (5.420, 5.520)
MECH_REF = (5.300, 5.320)      # right on the last mechanical peak


def dbfs(v):
    return round(float(20 * np.log10(np.sqrt(np.mean(np.asarray(v) ** 2)) + 1e-12)), 2)


def band_curve(x, fs=SR):
    # these windows are only 20-100 ms, so the segment length sets nperseg
    n = min(NPERSEG, len(x))
    n -= n % 2
    n = max(n, 64)
    f, P = signal.welch(x, fs=fs, nperseg=n, noverlap=n // 2, axis=0)
    P = P.mean(axis=1) if P.ndim > 1 else P
    return np.array([float(np.sum(P[(f >= lo) & (f < hi)])) for lo, hi in BANDS])


def row(label, x):
    bc = band_curve(x)
    return {'label': label, 'rms_dbfs': dbfs(x),
            'band_db': [round(float(10 * np.log10(v + 1e-30)), 1) for v in bc],
            'band_db_norm': [round(float(10 * np.log10(v + 1e-30)) - 10 * np.log10(bc.sum() + 1e-30), 1)
                             for v in bc]}


rows = []
for label, (a, b), src in (('tail (cleaned)', TAIL, clean),
                           ('wind after tail (cleaned)', WIND, clean),
                           ('last peak (cleaned)', MECH_REF, clean),
                           ('tail (RAW)', TAIL, raw),
                           ('wind after tail (RAW)', WIND, raw)):
    r = row(label, src[round(a * SR):round(b * SR)])
    r['span_s'] = [a, b]
    rows.append(r)

print('%-26s%11s   %s' % ('window', 'rms dBFS', 'band dB (200-400 ... 6.4-12k)'))
for r in rows:
    print('%-26s%11.2f   %s' % (r['label'], r['rms_dbfs'], r['band_db']))

print()
print('-- normalised band shape (removes level; shows whether it is the same material) --')
for r in rows:
    print('%-26s   %s' % (r['label'], r['band_db_norm']))

tail_shape = np.array([r for r in rows if r['label'] == 'tail (cleaned)'][0]['band_db_norm'])
wind_shape = np.array([r for r in rows if r['label'] == 'wind after tail (cleaned)'][0]['band_db_norm'])
peak_shape = np.array([r for r in rows if r['label'] == 'last peak (cleaned)'][0]['band_db_norm'])
print()
print('shape distance tail<->wind : %.2f dB' % float(np.sqrt(np.mean((tail_shape - wind_shape) ** 2))))
print('shape distance tail<->peak : %.2f dB' % float(np.sqrt(np.mean((tail_shape - peak_shape) ** 2))))
print('shape distance wind<->peak : %.2f dB' % float(np.sqrt(np.mean((wind_shape - peak_shape) ** 2))))

tail_db = [r for r in rows if r['label'] == 'tail (cleaned)'][0]['rms_dbfs']
wind_db = [r for r in rows if r['label'] == 'wind after tail (cleaned)'][0]['rms_dbfs']
peak_db = [r for r in rows if r['label'] == 'last peak (cleaned)'][0]['rms_dbfs']
print()
print('levels: last peak %+.2f, tail %+.2f, wind after tail %+.2f dBFS' % (peak_db, tail_db, wind_db))
print('tail is %.1f dB above the adjacent wind and %.1f dB below the peak.'
      % (tail_db - wind_db, peak_db - tail_db))

(OUT / 'close_tail_identity.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')