"""Diagnostic only: profile the delivered Eject asset to pin the wind gust.

Splits the delivered 430 ms Eject window into consecutive slices and reports the
wind-band level of each, so the exact stretch that carries the gust can be named.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

HERE = Path(__file__).resolve().parent
OUT = HERE / '_wind'
SR = 48000
WIND_BAND = (250, 1000)
MECH_BAND = (1500, 8000)

WINDOW = (1.800, 2.230)
raw, sr = sf.read(HERE / 'Analysis/715-reloading-decoded.wav', always_2d=True)
mono = raw.mean(axis=1)
sos = signal.butter(3, 200, fs=SR, btype='highpass', output='sos')
base = signal.sosfiltfilt(sos, mono, axis=0)


def bp(x, lo, hi):
    s = signal.butter(3, [lo, hi], fs=SR, btype='bandpass', output='sos')
    return signal.sosfiltfilt(s, x, axis=0)


a, b = WINDOW
seg = base[round(a * SR):round(b * SR)]
w = bp(seg, *WIND_BAND)
m = bp(seg, *MECH_BAND)

step = int(.020 * SR)
print('delivered Eject window %.3f-%.3f s, 20 ms slices' % (a, b))
print('%10s%12s%12s%12s' % ('slice s', 'wind dBFS', 'mech dBFS', 'wind-mech'))
rows = []
for i in range(0, len(w) - step, step):
    ws = float(20 * np.log10(np.sqrt(np.mean(w[i:i + step] ** 2)) + 1e-12))
    ms = float(20 * np.log10(np.sqrt(np.mean(m[i:i + step] ** 2)) + 1e-12))
    ts = a + i / SR
    rows.append({'t': round(ts, 3), 'wind_dbfs': round(ws, 1), 'mech_dbfs': round(ms, 1),
                 'margin_db': round(ws - ms, 1)})
    flag = '   <-- wind louder than mechanism' if ws > ms else ''
    print('%10.3f%12.1f%12.1f%12.1f%s' % (ts, ws, ms, ws - ms, flag))

print()
n_worse = sum(1 for r in rows if r['margin_db'] > 0)
print('%d of %d slices have the wind band at or above the mechanism band.' % (n_worse, len(rows)))
lead = [r for r in rows if r['t'] < 1.930]
mech = [r for r in rows if r['t'] >= 1.930]
print('in the lead-in (before 1.930 s): mean margin %+.1f dB over %d slices'
      % (float(np.mean([r['margin_db'] for r in lead])), len(lead)))
print('after 1.930 s:                   mean margin %+.1f dB over %d slices'
      % (float(np.mean([r['margin_db'] for r in mech])), len(mech)))

(OUT / 'eject_profile.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')