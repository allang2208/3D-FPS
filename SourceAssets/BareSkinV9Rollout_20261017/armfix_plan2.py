"""Offline: re-plan every dumped clip with the continuity guard (armfix.plan). Clips whose result differs from what
armfix_write wrote (Work/ArmPlan) get a new plan in Work/ArmPlan2: guarded sides are re-planned, sides that end up
unchanged get their pre-armfix rotations back (from the dump). Summary in Work/armfix2_summary.json."""
import json
import numpy as np
from scipy.spatial.transform import Rotation as Rot
from rollout import R, load_snapshot
import armfix, reroute as rr

jobs = json.loads((R / 'Work/armfix_jobs.json').read_text())
import os
OUT = R / os.environ.get('V9R_ARM_OUT', 'Work/ArmPlan2'); OUT.mkdir(exist_ok=True)
PREV = [x for x in os.environ.get('V9R_ARM_PREV', 'Work/ArmPlan').split(',') if x]     # latest written plan listed last
BONES = ('upperarm', 'lowerarm', 'hand', 'lowerarm_twist_01', 'lowerarm_twist_02')
refs = {}; summary = []; n_guard = 0


def ang(a, b):
    return np.degrees(2 * np.arccos(np.clip(np.abs(np.sum(np.asarray(a) * np.asarray(b), axis=-1)), 0, 1)))


for f in sorted((R / 'Work/ArmDump').glob('*.json')):
    pfs = [R / x / f.name for x in PREV if (R / x / f.name).exists()]
    if not pfs: continue
    pf = pfs[-1]
    d = json.loads(f.read_text()); old = json.loads(pf.read_text()); path = d['path']; job = jobs[path]; vm = d['vm']
    if vm not in refs: refs[vm] = load_snapshot(vm)['bones']
    ref = refs[vm]
    names = d['names']; idx = {x: i for i, x in enumerate(names)}; parents = d['parents']
    comp = []
    for key in d['keys']:
        C = {}
        for i, x in enumerate(names):
            t = np.array(key[i][:3]); q = Rot.from_quat(key[i][3:]); p_ = parents[i]
            if p_ in C: Pt, Pq = C[p_]; C[x] = (Pt + Pq.apply(t), Pq * q)
            else: C[x] = (t, q)
        comp.append(C)
    new = dict(path=path, n=d['n'], sides={}); info = {}; differs = False
    for s, rows_old in old['sides'].items():
        sd = job['sides'][s]
        keys = [dict(S=C['upperarm_' + s][0], E=C['lowerarm_' + s][0], W=C['hand_' + s][0], U=C['upperarm_' + s][1], L=C['lowerarm_' + s][1],
                     H=C['hand_' + s][1]) for C in comp]
        pl = armfix.plan(keys, ref, s, sd, d['rate'])
        rows = {}
        if pl['changed']:
            cla = 'clavicle_' + s
            for b in BONES: rows[b + '_' + s] = []
            for C, k, a, b_, g, pfin in zip(comp, keys, pl['alpha'], pl['beta'], pl['gamma'], pl['p_final']):
                U2, L2, H2, T1, T2 = armfix.rotations(k, a, b_, g, pfin, sd)
                Cq = C[cla][1] if cla in C else Rot.identity()
                for b, q in (('upperarm', Cq.inv() * U2), ('lowerarm', U2.inv() * L2), ('hand', L2.inv() * H2),
                             ('lowerarm_twist_01', L2.inv() * T1), ('lowerarm_twist_02', L2.inv() * T2)):
                    rows[b + '_' + s].append([round(float(x), 8) for x in q.as_quat()])
        else:                                                   # back to the pre-armfix keys
            for b in BONES: rows[b + '_' + s] = [[round(float(x), 8) for x in key[idx[b + '_' + s]][3:]] for key in d['keys']]
        dev = max(float(ang(np.array(rows[b]), np.array(rows_old[b])).max()) for b in rows)
        if dev > .5: differs = True
        new['sides'][s] = rows
        guarded = pl['elbow_keys'] == 0 and not pl['windows']
        n_guard += dev > .5
        info[s] = dict(changed=pl['changed'], elbow_keys=pl['elbow_keys'], windows=[w[2] for w in pl['windows']], deviation_from_written=round(dev, 1))
    if differs:
        new['info'] = info; (OUT / f.name).write_text(json.dumps(new, separators=(',', ':'))); summary.append((path, info))
(R / 'Work/armfix2_summary.json').write_text(json.dumps(summary, indent=1))
print('clips to rewrite', len(summary), 'sides changed vs written', n_guard)
for p, i in summary[:40]: print(' ', p.split('/')[-1], {s: (v['elbow_keys'], v['windows'], v['deviation_from_written']) for s, v in i.items()})
