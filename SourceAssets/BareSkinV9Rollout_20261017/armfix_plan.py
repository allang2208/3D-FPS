"""Offline: full-rate arm axial fix for every dumped clip (Work/ArmDump) -> new local rotations of upperarm, lowerarm,
hand and the two forearm twist bones per changed side (Work/ArmPlan/<hash>.json), and a summary."""
import json, math
import numpy as np
from scipy.spatial.transform import Rotation as Rot
from rollout import R, load_snapshot
import armfix, elbow_hinge as eh, reroute as rr

jobs = json.loads((R / 'Work/armfix_jobs.json').read_text())
OUT = R / 'Work/ArmPlan'; OUT.mkdir(exist_ok=True)
refs = {}; summary = []
for f in sorted((R / 'Work/ArmDump').glob('*.json')):
    d = json.loads(f.read_text()); path = d['path']; job = jobs[path]; vm = d['vm']
    refs.setdefault(vm, load_snapshot(vm)['bones']); ref = refs[vm]
    names = d['names']; idx = {x: i for i, x in enumerate(names)}; parents = d['parents']
    comp = []
    for key in d['keys']:
        C = {}
        for i, x in enumerate(names):
            t = np.array(key[i][:3]); q = Rot.from_quat(key[i][3:]); p_ = parents[i]
            if p_ in C: Pt, Pq = C[p_]; C[x] = (Pt + Pq.apply(t), Pq * q)
            else: C[x] = (t, q)
        comp.append(C)
    out = dict(path=path, n=d['n'], sides={}); info = {}
    for s, sd in job['sides'].items():
        keys = [dict(S=C['upperarm_' + s][0], E=C['lowerarm_' + s][0], W=C['hand_' + s][0], U=C['upperarm_' + s][1], L=C['lowerarm_' + s][1],
                     H=C['hand_' + s][1]) for C in comp]
        pl = armfix.plan(keys, ref, s, sd, d['rate'])
        # always rewrite the twist bones of a planned side from p_final (consistent with the new forearm)
        side = eh.Side(ref, s, sd['rel_hand'], sd['axis_l'])
        p_old = rr.unwrap([rr.twist((k['L'].inv() * k['H'] * side.rel_hand.inv()).as_quat(), side.axis) for k in keys])
        if not pl['changed'] and np.abs(p_old).max() <= 175: continue
        cla = 'clavicle_' + s
        rows = {b: [] for b in ('upperarm', 'lowerarm', 'hand', 'lowerarm_twist_01', 'lowerarm_twist_02')}
        for C, k, a, b_, g, pf in zip(comp, keys, pl['alpha'], pl['beta'], pl['gamma'], pl['p_final']):
            U2, L2, H2, T1, T2 = armfix.rotations(k, a, b_, g, pf, sd)
            Cq = C[cla][1] if cla in C else Rot.identity()
            for b, q in (('upperarm', Cq.inv() * U2), ('lowerarm', U2.inv() * L2), ('hand', L2.inv() * H2),
                         ('lowerarm_twist_01', L2.inv() * T1), ('lowerarm_twist_02', L2.inv() * T2)):
                rows[b].append([round(float(x), 8) for x in q.as_quat()])
        out['sides'][s] = {b + '_' + s: v for b, v in rows.items()}
        info[s] = dict(windows=[w[2] for w in pl['windows']], elbow_keys=pl['elbow_keys'], hand_max=round(float(np.abs(pl['gamma']).max()), 1),
                       forearm_max=round(float(np.abs(pl['beta']).max()), 1), upper_max=round(float(np.abs(pl['alpha']).max()), 1),
                       roll_before=[round(float(p_old.min())), round(float(p_old.max()))],
                       roll_after=[round(float(np.min(pl['p_final']))), round(float(np.max(pl['p_final'])))])
    if out['sides']:
        out['info'] = info; (OUT / f.name).write_text(json.dumps(out, separators=(',', ':'))); summary.append((path, info))
(R / 'Work/armfix_summary.json').write_text(json.dumps(summary, indent=1))
print('planned clips', len(summary), 'sides', sum(len(i) for _, i in summary),
      '| hand re-routed', sum(1 for _, i in summary for v in i.values() if v['hand_max'] > 1),
      '| re-route windows', sum(1 for _, i in summary for v in i.values() if 'reroute' in v['windows']),
      '| still beyond 175', sum(1 for _, i in summary for v in i.values() if max(map(abs, v['roll_after'])) > 175))
