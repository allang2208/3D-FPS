"""Write the R26 push clock header and its timing record (no pose change)."""
import json
from pathlib import Path
import numpy as np
import r26_timing as T

O = Path(__file__).parent
P = O.parents[1]
H = P / 'Source/FPSGAME/Weapons/Super90LoaderPushTiming.h'
before = O / 'Before/Source/Super90LoaderPushTiming.h'
if not before.exists():
    before.parent.mkdir(parents=True, exist_ok=True)
    before.write_bytes(H.read_bytes())
H.write_text(T.header(), encoding='utf-8')

# R25 knots, only for the comparison record.
R25 = [(86., 86., 1.), (104., 92.502451001, .620325796), (113., 105.6, 1.461901993), (116., 110., 1.)]
def r25(p):
    for (pa, sa, ma), (pb, sb, mb) in zip(R25, R25[1:]):
        if p <= pb:
            d = pb - pa; t = (p - pa) / d
            return (6*t*t - 6*t) * (sa - sb) / d + (3*t*t - 4*t + 1) * ma + (3*t*t - 2*t) * mb
pace = np.arange(86., 116.01, 1.)
audio = json.loads((O.parent / 'Super90LoaderR16_20261009/audio_provenance.json').read_text())
record = dict(revision='Super90LoaderR26-20261016', fps=60, base_rate=1.3,
    split_source_frame=T.SPLIT, align_pace=[86, 104], drive_pace=[104, 116], extra_pace_frames=6,
    knots=[dict(pace=p, source=s, slope=m) for p, s, m in T.KNOTS],
    slope_r25=[round(float(r25(p)), 4) for p in pace], slope_r26=[round(T.slope(p), 4) for p in pace],
    min_alignment_slope_r25=float(min(r25(p) for p in np.linspace(86, 104, 1801))),
    min_alignment_slope_r26=float(min(T.slope(p) for p in np.linspace(86.5, 104, 1751))),
    dock_pace_frame=T.pace_frame(87.012105),
    cues=[dict(asset=c['asset'], source_frame=c['animation_frame'], pace_frame=T.pace_frame(c['animation_frame']))
          for c in audio['audio']], runtime_tested=False)
(O / 'timing.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print('R26_TIMING', json.dumps({k: record[k] for k in ('min_alignment_slope_r25', 'min_alignment_slope_r26', 'dock_pace_frame')}))
for p, a, b in zip(pace, record['slope_r25'], record['slope_r26']):
    print(f'  pace {p:5.0f}  R25 {a:5.2f}x  R26 {b:5.2f}x  source {T.source_frame(p):8.3f}')
