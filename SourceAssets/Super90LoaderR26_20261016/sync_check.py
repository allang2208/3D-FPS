"""Author-side: does each left-hand event still meet its audio cue? (R25 installed vs R26a vs R26b)."""
import json
import numpy as np
from r26_core import *

CUES = dict(Dock=87.012105, Drive=99.585985, Seat=110., Detach=123.464567)
patches = {'R26a': json.loads((O / 'animation_patch_r26a.json').read_text()),
           'R26b': json.loads((O / 'animation_patch.json').read_text())}


def rows_for(role, patch):
    rows = posed_local(role)
    if patch:
        for t in patch['clips'][role]['tracks']:
            v = np.array(t['values']).reshape(-1, 10)
            for f, r in enumerate(rows):
                r[t['bone']] = v[f] if len(v) > 1 else v[0]
    return rows


report = {}
for role in ('normal_7', 'empty_7'):
    out = {}
    base = None
    for name, patch in (('R25', None), *patches.items()):
        W = [world(r) for r in rows_for(role, patch)]
        P = np.array([(np.linalg.inv(w[GUN]) @ w['hand_l'])[:3, 3] for w in W])
        v = np.linalg.norm(np.diff(P, axis=0), axis=1) * FPS
        swing = next(f for f in range(119, len(v)) if v[f] > .25)
        after = 0. if base is None else float(np.abs(P[124:] - base[124:]).max() * 1000)
        out[name] = dict(swing_start_frame=swing, min_speed_116_123=float(v[116:123].min()),
                         hand_mm_after_124_vs_R25=round(after, 3))
        base = P if base is None else base
    report[role] = out
    print(role, json.dumps(out))
print('Detach cue source frame', CUES['Detach'])
(O / 'sync_check.json').write_text(json.dumps(dict(cues=CUES, clips=report), indent=1))
