"""Diagnostic only: per-slice wind vs mechanism for both problem clips.

Applies one identical method to Eject and Close so the two can be compared
directly, and so the rebuild can replace exactly the slices where wind leads.
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

WINDOWS = [('Eject', 1.800, 2.230, 2.056), ('Close', 4.940, 5.420, 5.313)]

raw, sr = sf.read(HERE / 'Analysis/715-reloading-decoded.wav', always_2d=True)
mono = raw.mean(axis=1)
sos = signal.butter(3, 200, fs=SR, btype='highpass', output='sos')
base = signal.sosfiltfilt(sos, mono, axis=0)


def bp(x, lo, hi):
    s = signal.butter(3, [lo, hi], fs=SR, btype='bandpass', output='sos')
    return signal.sosfiltfilt(s, x, axis=0)


summary = {}
for name, a, b, peak_t in WINDOWS:
    seg = base[round(a * SR):round(b * SR)]
    w, m = bp(seg, *WIND_BAND), bp(seg, *MECH_BAND)
    step = int(.020 * SR)
    rows = []
    for i in range(0, len(w) - step, step):
        ws = float(20 * np.log10(np.sqrt(np.mean(w[i:i + step] ** 2)) + 1e-12))
        ms = float(20 * np.log10(np.sqrt(np.mean(m[i:i + step] ** 2)) + 1e-12))
        rows.append({'t': round(a + i / SR, 3), 'wind': round(ws, 1), 'mech': round(ms, 1),
                     'margin': round(ws - ms, 1), 'wind_leads': bool(ws > ms)})
    lead = sum(1 for r in rows if r['wind_leads'])
    # contiguous stretches where wind leads, at least 40 ms
    runs, start = [], None
    for i, r in enumerate(rows):
        if r['wind_leads'] and start is None:
            start = i
        elif not r['wind_leads'] and start is not None:
            if (i - start) * 20 >= 40:
                runs.append([rows[start]['t'], round(rows[i - 1]['t'] + .02, 3)])
            start = None
    if start is not None and (len(rows) - start) * 20 >= 40:
        runs.append([rows[start]['t'], round(rows[-1]['t'] + .02, 3)])
    summary[name] = {
        'window_s': [a, b], 'impact_s': peak_t,
        'slices': len(rows), 'wind_leads_slices': lead,
        'wind_leads_pct': round(100 * lead / len(rows), 1),
        'mean_margin_db': round(float(np.mean([r['margin'] for r in rows])), 1),
        'worst_margin_db': round(float(np.max([r['margin'] for r in rows])), 1),
        'wind_led_runs': runs,
        'rows': rows,
    }
    print('== %s  (%.3f-%.3f s, impact at %.3f) ==' % (name, a, b, peak_t))
    print('   wind band leads the mechanism band in %d/%d slices (%.0f%%); '
          'mean margin %+.1f dB, worst %+.1f dB'
          % (lead, len(rows), 100 * lead / len(rows), summary[name]['mean_margin_db'],
             summary[name]['worst_margin_db']))
    print('   20 ms slices where wind leads (wind dB / mech dB):')
    for r in rows:
        mark = '  <<' if r['wind_leads'] else ''
        print('      %.3f  %7.1f  %7.1f  %+6.1f%s' % (r['t'], r['wind'], r['mech'], r['margin'], mark))
    print('   contiguous wind-led stretches >=40 ms:')
    for s, e in runs:
        print('      %.3f - %.3f  (%.0f ms)' % (s, e, (e - s) * 1000))
    print()

(OUT / 'slice_compare.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')