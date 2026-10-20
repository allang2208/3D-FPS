"""Author input: clock slope and perceived pusher rate for R25 / R26 / R27 (no pose change)."""
import json, sys
from pathlib import Path
import numpy as np
O = Path(__file__).parent
sys.path.insert(0, str(O.parent / 'Super90LoaderR26_20261016'))
import r26_timing as R26
import r27_timing as R27

R25 = [(86., 86., 1.), (104., 92.502451001, .620325796), (113., 105.6, 1.461901993), (116., 110., 1.)]
def r25_source(p):
    for a, b in zip(R25, R25[1:]):
        if p <= b[0]:
            return R27._hermite(p, a, b)
# Pusher progress per source frame from the installed clip (R26 measure.json, linear between keys).
m = json.loads((O.parent / 'Super90LoaderR26_20261016/measure.json').read_text())['normal_7']['rows']
src = np.array([r['f'] for r in m], float); stroke = np.array([r['stroke'] for r in m])
def rate(fn, p, h=.05):
    return (np.interp(fn(p + h), src, stroke) - np.interp(fn(p - h), src, stroke)) / (2 * h)
def slope(fn, p, h=1e-3):
    return (fn(p + h) - fn(p - h)) / (2 * h)
clocks = dict(R25=r25_source, R26=R26.source_frame, R27=R27.source_frame)
rows = []
print('pace   slope R25  R26  R27 | stroke %/pace-frame R25  R26  R27 | stroke R27')
for p in np.arange(86., 116.01, 1.):
    q = min(p, 115.95) if p > 86 else 86.05
    s = {k: slope(f, q) for k, f in clocks.items()}
    r = {k: rate(f, q) * 100 for k, f in clocks.items()}
    rows.append(dict(pace=p, slope=s, stroke_rate_pct=r))
    print('%5.0f   %5.2f %5.2f %5.2f | %6.2f %6.2f %6.2f | %5.1f%%' % (p, s['R25'], s['R26'], s['R27'],
          r['R25'], r['R26'], r['R27'], np.interp(R27.source_frame(p), src, stroke) * 100))
mono = all(b > a for a, b in zip([R27.source_frame(x) for x in np.linspace(86, 116, 3001)][:-1],
                                 [R27.source_frame(x) for x in np.linspace(86, 116, 3001)][1:]))
drive = [slope(R27.source_frame, x) for x in np.linspace(104.2, 114.4, 400)]
print('R27 monotone clock:', mono, '| drive slope monotone rising:', all(b >= a - 1e-6 for a, b in zip(drive, drive[1:])),
      '| peak', round(max(slope(R27.source_frame, x) for x in np.linspace(104, 116, 1201)), 3))
for name, frame in (('Dock', 87.012105), ('Drive', 99.585985), ('Seat', 110.)):
    print('cue %-5s source %.2f -> pace R25 %.2f  R27 %.2f' % (name, frame,
          next(x for x in np.linspace(86, 116, 30001) if r25_source(x) >= frame), R27.pace_frame(frame)))
(O / 'timing_comparison.json').write_text(json.dumps(rows, indent=1))
