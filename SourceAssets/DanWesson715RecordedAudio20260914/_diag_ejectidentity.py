"""Diagnostic only: same identity test for Eject's lead-in.

The Close tail turned out to be mechanism, not wind, so the trim decision must be
re-checked.  This measures Eject's pre-impact lead-in against its own mechanism
and against wind-only material, to see which it actually is.
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

WINDOWS = [
    ('eject lead (1.700-1.930)', 1.700, 1.930),
    ('eject impact (1.930-2.075)', 1.930, 2.075),
    ('eject decay (2.075-2.230)', 2.075, 2.230),
    ('pure wind (0.555-1.055)', 0.555, 1.055),
    ('pure wind (2.230-2.757)', 2.230, 2.757),
    ('quietest stretch (4.385-4.915)', 4.385, 4.915),
]


def band_curve(x, fs=SR):
    n = min(NPERSEG, len(x))
    n -= n % 2
    n = max(n, 64)
    f, P = signal.welch(x, fs=fs, nperseg=n, noverlap=n // 2, axis=0)
    P = P.mean(axis=1) if P.ndim > 1 else P
    bc = np.array([float(np.sum(P[(f >= lo) & (f < hi)])) for lo, hi in BANDS])
    tot = float(bc.sum())
    return bc, np.array([10 * np.log10(v + 1e-30) - 10 * np.log10(tot + 1e-30) for v in bc])


rows = []
for label, a, b in WINDOWS:
    bc, shape = band_curve(clean[round(a * SR):round(b * SR)])
    rbc, rshape = band_curve(raw[round(a * SR):round(b * SR)])
    rows.append({'label': label, 'span_s': [a, b],
                 'rms_dbfs': round(float(20 * np.log10(np.sqrt(np.mean(
                     clean[round(a * SR):round(b * SR)] ** 2)) + 1e-12)), 2),
                 'raw_rms_dbfs': round(float(20 * np.log10(np.sqrt(np.mean(
                     raw[round(a * SR):round(b * SR)] ** 2)) + 1e-12)), 2),
                 'shape': [round(float(v), 1) for v in shape],
                 'raw_shape': [round(float(v), 1) for v in rshape]})

print('%-32s%10s%10s   %s' % ('window', 'rms dB', 'raw dB', 'normalised band shape'))
for r in rows:
    print('%-32s%10.2f%10.2f   %s' % (r['label'], r['rms_dbfs'], r['raw_rms_dbfs'], r['shape']))

lead = np.array(rows[0]['shape'])
impact = np.array(rows[1]['shape'])
wind = np.array(rows[3]['shape'])
wind2 = np.array(rows[4]['shape'])
quiet = np.array(rows[5]['shape'])
rlead = np.array(rows[0]['raw_shape'])
rwind = np.array(rows[3]['raw_shape'])
rimpact = np.array(rows[1]['raw_shape'])


def dist(a, b):
    return round(float(np.sqrt(np.mean((a - b) ** 2))), 2)


print()
print('== clean-source shape distances ==')
print('   eject lead <-> eject impact : %.2f dB' % dist(lead, impact))
print('   eject lead <-> pure wind    : %.2f dB' % dist(lead, wind))
print('   eject lead <-> pure wind 2  : %.2f dB' % dist(lead, wind2))
print('   eject lead <-> quietest     : %.2f dB' % dist(lead, quiet))
print('   eject impact <-> pure wind  : %.2f dB' % dist(impact, wind))
print()
print('== raw-source shape distances (before any wind reduction) ==')
print('   eject lead <-> eject impact : %.2f dB' % dist(rlead, rimpact))
print('   eject lead <-> pure wind    : %.2f dB' % dist(rlead, rwind))

print()
print('level of the eject lead: %+.2f dBFS (cleaned), %+.2f dBFS (raw)'
      % (rows[0]['rms_dbfs'], rows[0]['raw_rms_dbfs']))
print('pure-wind stretches sit at: %+.2f / %+.2f dBFS (cleaned)'
      % (rows[3]['rms_dbfs'], rows[4]['rms_dbfs']))

(OUT / 'eject_identity.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')