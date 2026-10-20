"""Authoring check: the shipped M4 clips skinned with and without the JC_ correctives (same driver as C++).

Counts triangles in the joint zones that turn against their bind orientation and records driver weights.
Writes Work/validate_anim.json. This is a production check of the offline data, not a game test.
"""
import json
import numpy as np
from scipy.spatial.transform import Rotation as Rot
exec(open(__file__.replace('validate_anim.py', 'correctives.py')).read().split('shapes = {}; meta = {}')[0])

meta = json.loads((R / 'Work/correctives.json').read_text()); shp = np.load(R / 'Work/correctives.npz')
ref_mats = {n: (ref_q[n].as_matrix(), ref_t[n]) for n in names}
tw = wv[m.T]
fr0 = np.cross(P[tw[:, 1]] - P[tw[:, 0]], P[tw[:, 2]] - P[tw[:, 0]])
zones = {}
for s in ('l', 'r'):
    on = (P[:, 0] < 0) if s == 'l' else (P[:, 0] > 0)
    near = on & ((np.linalg.norm(P - ref_t['lowerarm_' + s], axis=1) < 9) | (np.linalg.norm(P - ref_t['hand_' + s], axis=1) < 6))
    zones[s] = near[tw].any(axis=1)


def tent(x, a, b, c): return np.clip((x - a) / (b - a), 0, 1) if x <= b else np.clip((c - x) / (c - b), 0, 1)


def drive(t, q, s):
    i = {n: k for k, n in enumerate(names)}
    U = t[i['lowerarm_' + s]] - t[i['upperarm_' + s]]; F = t[i['hand_' + s]] - t[i['lowerarm_' + s]]
    e = np.degrees(np.arccos(np.clip(U @ F / np.linalg.norm(U) / np.linalg.norm(F), -1, 1)))
    rest = meta['frame_' + s]['rest_elbow_deg']
    w = {f'JC_ElbowFlex20_{s.upper()}': float(np.clip((rest - e) / (rest - 20), 0, 1)),
         f'JC_ElbowFlex75_{s.upper()}': tent(e, rest, 75, 110), f'JC_ElbowFlex110_{s.upper()}': tent(e, 75, 110, 135),
         f'JC_ElbowFlex135_{s.upper()}': float(np.clip((e - 110) / 25, 0, 1))}
    h = q[i['lowerarm_twist_01_' + s]].inv().apply(t[i['middle_01_' + s]] - t[i['hand_' + s]]); h /= np.linalg.norm(h)
    f0, r0, z0 = (np.array(meta['frame_' + s][k]) for k in ('f0_twist', 'r0_twist', 'z0_twist'))
    flex = np.degrees(np.arctan2(-(h @ z0), h @ f0)); dev = np.degrees(np.arctan2(h @ r0, h @ f0))
    sane = 1 - smoothstep(95, 135, max(abs(flex), abs(dev)))
    w.update({f'JC_WristFlexA_{s.upper()}': np.clip(flex / 40, 0, 1) * sane, f'JC_WristFlexB_{s.upper()}': np.clip(-flex / 40, 0, 1) * sane,
              f'JC_WristRadial_{s.upper()}': np.clip(dev / 20, 0, 1) * sane, f'JC_WristUlnar_{s.upper()}': np.clip(-dev / 35, 0, 1) * sane})
    extra = []
    for f in ('index', 'middle', 'ring', 'pinky'):
        a = t[i[f'{f}_01_{s}']] - t[i[f'{f}_metacarpal_{s}']]; b = t[i[f'{f}_02_{s}']] - t[i[f'{f}_01_{s}']]
        extra.append(np.degrees(np.arccos(np.clip(a @ b / np.linalg.norm(a) / np.linalg.norm(b), -1, 1))) - meta[f'mcp_{f}_{s}']['rest_deg'])
    for name in shp.files if hasattr(shp, 'files') else shp:
        if name.startswith(f'JC_Grip_{s.upper()}_'):             # radial basis on the four MCP angles (same as C++)
            ex = [float(x) for x in name.split('_')[3:7]]
            w[name] = float(np.exp(-.5 * sum(((max(x, 0) - e_) / 12.0) ** 2 for x, e_ in zip(extra, ex))))
    return w, e, flex, dev


report = {}
for clip, c in rd['clips'].items():
    if c.get('missing'): continue
    rows = []
    for fi in range(0, len(c['frames']), 3):
        fr = c['frames'][fi]
        t = np.array([b['t'] for b in fr]); q = Rot.from_quat([b['q'] for b in fr])
        Rm = np.zeros((len(bones_used), 3, 3)); Tv = np.zeros((len(bones_used), 3))
        for k, b in enumerate(bones_used):
            j = names.index(b); Mp = q[j].as_matrix(); Mr, tr = ref_mats[b]
            Rm[k] = Mp @ Mr.T; Tv[k] = t[j] - Rm[k] @ tr
        Xb, A = lbs(P, Rm, Tv)
        delta = np.zeros_like(P); weights = {}
        for s in ('l', 'r'):
            w, e, fl, dv = drive(t, q, s); weights[s] = dict(elbow=round(float(e), 1), flex=round(float(fl), 1), dev=round(float(dv), 1))
            for name, x in w.items():
                if x > 0: delta += shp[name] * x
        Xc, _ = lbs(P + delta, Rm, Tv)
        Rr = A[tw[:, 0]]; fr2 = np.einsum('vij,vj->vi', Rr, fr0)
        def folded(Xa, s):
            fa = np.cross(Xa[tw[:, 1]] - Xa[tw[:, 0]], Xa[tw[:, 2]] - Xa[tw[:, 0]])
            return int(((np.einsum('ij,ij->i', fa, fr2) < 0) & zones[s]).sum())
        def holes(Xa, s):                                        # faces against their own vertex normals in the hand
            return int(len(inverted(Xa, (m.region == 2) & ((P[tw].mean(axis=1)[:, 0] < 0) == (s == 'l')))))
        rows.append(dict(frame=fi, **{s: dict(weights[s], folded_lbs=folded(Xb, s), folded_jc=folded(Xc, s), hand_holes_lbs=holes(Xb, s),
                                              hand_holes_jc=holes(Xc, s)) for s in ('l', 'r')},
                         max_morph_cm=round(float(np.linalg.norm(delta, axis=1).max()), 3)))
    report[clip.split('/')[-1]] = dict(frames=len(rows),
        folded_lbs={s: max(r[s]['folded_lbs'] for r in rows) for s in ('l', 'r')},
        folded_jc={s: max(r[s]['folded_jc'] for r in rows) for s in ('l', 'r')},
        hand_holes_lbs={s: max(r[s]['hand_holes_lbs'] for r in rows) for s in ('l', 'r')},
        hand_holes_jc={s: max(r[s]['hand_holes_jc'] for r in rows) for s in ('l', 'r')},
        elbow={s: [min(r[s]['elbow'] for r in rows), max(r[s]['elbow'] for r in rows)] for s in ('l', 'r')},
        max_morph_cm=max(r['max_morph_cm'] for r in rows))
    print(clip.split('/')[-1], json.dumps(report[clip.split('/')[-1]]))
(R / 'Work/validate_anim.json').write_text(json.dumps(report, indent=1))
