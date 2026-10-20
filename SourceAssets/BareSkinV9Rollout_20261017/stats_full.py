"""Offline, full key rate, every side the arm fix looked at (Work/ArmDump = keys before the fix; armfix.plan = what
the assets now hold within 0.5 deg): hand roll range, worst per-key jump, elbow axial roll, before / after."""
import json
import numpy as np
from scipy.spatial.transform import Rotation as Rot
from rollout import R, load_snapshot
import armfix, elbow_hinge as eh, reroute as rr

jobs = json.loads((R / 'Work/armfix_jobs.json').read_text()); refs = {}
st = dict(sides=0, roll180_b=0, roll180_a=0, e90_b=0, e90_a=0, e120_b=0, e120_a=0, jump30_b=0, jump30_a=0, hand_turned=0, elbow_fixed=0, rerouted=0)
for f in sorted((R / 'Work/ArmDump').glob('*.json')):
    d = json.loads(f.read_text()); job = jobs[d['path']]; refs.setdefault(d['vm'], load_snapshot(d['vm'])['bones']); ref = refs[d['vm']]
    names, parents = d['names'], d['parents']; comp = []
    for key in d['keys']:
        C = {}
        for i, x in enumerate(names):
            t = np.array(key[i][:3]); q = Rot.from_quat(key[i][3:]); p_ = parents[i]
            C[x] = (C[p_][0] + C[p_][1].apply(t), C[p_][1] * q) if p_ in C else (t, q)
        comp.append(C)
    for s, sd in job['sides'].items():
        keys = [dict(S=C['upperarm_' + s][0], E=C['lowerarm_' + s][0], W=C['hand_' + s][0], U=C['upperarm_' + s][1], L=C['lowerarm_' + s][1], H=C['hand_' + s][1]) for C in comp]
        side = eh.Side(ref, s, sd['rel_hand'], sd['axis_l'])
        p0 = rr.unwrap([rr.twist((k['L'].inv() * k['H'] * side.rel_hand.inv()).as_quat(), side.axis) for k in keys]); p0 -= 360 * round(float(np.mean(p0)) / 360)
        e0 = [abs(eh.wrap(eh.twist(((k['U'] * side.B).inv() * k['L']).as_quat(), side.axis))) for k in keys]
        pl = armfix.plan(keys, ref, s, sd, d['rate']); p1 = np.asarray(pl['p_final']); e1 = []
        for k, a, b_, g, pf in zip(keys, pl['alpha'], pl['beta'], pl['gamma'], pl['p_final']):
            U2, L2, H2, _, _ = armfix.rotations(k, a, b_, g, pf, sd); e1.append(abs(eh.wrap(eh.twist(((U2 * side.B).inv() * L2).as_quat(), side.axis))))
        lim = 30.0 * 120.0 / d['rate']                               # a 30 deg jump at 120 fps, scaled to the clip's rate
        st['sides'] += 1
        st['roll180_b'] += np.abs(p0).max() > 180; st['roll180_a'] += np.abs(p1).max() > 180
        st['e90_b'] += max(e0) > 90; st['e90_a'] += max(e1) > 90; st['e120_b'] += max(e0) > 120; st['e120_a'] += max(e1) > 120
        jb = len(p0) > 1 and np.abs(np.diff(p0)).max() > lim; ja = len(p1) > 1 and np.abs(np.diff(p1)).max() > lim
        st['jump30_b'] += jb; st['jump30_a'] += ja
        if ja and not jb:
            print('NEWJUMP', d['path'].split('/')[-1], s, round(float(np.abs(np.diff(p0)).max()), 1), '->', round(float(np.abs(np.diff(p1)).max()), 1),
                  'rate', d['rate'], [w[2] for w in pl['windows']], pl['elbow_keys'], flush=True)
        gw = np.abs(((np.asarray(pl['gamma']) + 180) % 360) - 180)       # whole turns are no change
        st['hand_turned'] += gw.max() > 1
        if gw.max() > 1:
            print('HANDTURN', d['path'].split('/')[-1], s, 'max %.0f deg, %d keys (%.2fs)' % (gw.max(), (gw > 1).sum(), (gw > 1).sum() / d['rate']), flush=True)
        st['elbow_fixed'] += pl['elbow_keys'] > 0; st['rerouted'] += bool(pl['windows'])
print({k: int(v) for k, v in st.items()})
(R / 'Work/stats_full.json').write_text(json.dumps({k: int(v) for k, v in st.items()}))
