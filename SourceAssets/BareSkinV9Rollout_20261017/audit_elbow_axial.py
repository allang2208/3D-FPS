"""Offline (ClipsTrue): per clip side, the forearm bone's axial roll inside the elbow (lowerarm vs upperarm, against
bind; a pure hinge is 0) - per frame wrapped to +-180, i.e. what the elbow skin actually shows."""
import json, collections
import numpy as np
from scipy.spatial.transform import Rotation as Rot
from rollout import R, load_snapshot
from unspin import twist, elbow_twist

rows = []; seen = set()
for b in ('batch1', 'batch2', 'batch3', 'batch4'):
    plan = json.loads((R / (b + '.json')).read_text()); specs = json.loads((R / 'Work' / b / 'twist_specs.json').read_text())
    for ps, vm in plan['viewmodels'].items():
        f = R / 'ClipsTrue' / (ps + '.json')
        if not f.exists(): continue
        ref = load_snapshot(vm)['bones']; cd = json.loads(f.read_text()); bi = {x: i for i, x in enumerate(cd['bones'])}
        for s in 'lr':
            if 'lowerarm_' + s not in bi: continue
            U0 = Rot.from_quat(ref['upperarm_' + s]['q']); L0 = Rot.from_quat(ref['lowerarm_' + s]['q'])
            ax = L0.inv().apply(np.asarray(ref['hand_' + s]['t']) - ref['lowerarm_' + s]['t']); ax /= np.linalg.norm(ax)
            for path, c in cd['clips'].items():
                if 'frames' not in c or (path, s) in seen: continue
                seen.add((path, s))
                e = [elbow_twist(Rot.from_quat(fr[bi['upperarm_' + s]][3:]), Rot.from_quat(fr[bi['lowerarm_' + s]][3:]), U0, L0, ax) for fr in c['frames']]
                rows.append((path, s, max(abs(x) for x in e), sum(abs(x) > 90 for x in e) / len(e)))
cnt = collections.Counter()
for lim in (60, 90, 120, 150):
    print('sides with elbow axial roll beyond %d deg at some frame: %d of %d' % (lim, sum(1 for r in rows if r[2] > lim), len(rows)))
print('worst:')
for r in sorted(rows, key=lambda x: -x[2])[:40]: print('  %-48s %s max %3d  frames>90: %.0f%%' % (r[0].split('/')[-1][:48], r[1], r[2], 100 * r[3]))
(R / 'Work/elbow_axial_audit.json').write_text(json.dumps(rows))
