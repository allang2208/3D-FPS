"""Grip example poses (pose-space correctives) for the M4 hands, appended to Work/correctives.npz.

The palmar crease at the finger bases folds through only when the fingers curl together around a grip,
which single-joint keys cannot reproduce. One example per persistent held grip (HELD): A_AKM_idle (idle /
aim / fire / equip, both hands) and the vertical-foregrip idle (left hand). Each example is skinned with every other corrective at its
runtime weight, its hand folds are untangled by local relaxation, and the rest is pulled back to the
reference pose. Driver: radial basis on the four MCP angles, example angles encoded in the morph name
(JC_Grip_<L|R>_<index>_<middle>_<ring>_<pinky>, degrees past bind), so the runtime needs no table.
"""
import json
import numpy as np
from scipy.spatial.transform import Rotation as Rot
exec(open(__file__.replace('grip_correctives.py', 'correctives.py')).read().split('shapes = {}; meta = {}')[0])
va = open(__file__.replace('grip_correctives.py', 'validate_anim.py')).read()
meta = json.loads((R / 'Work/correctives.json').read_text())
shp = {k: v for k, v in dict(np.load(R / 'Work/correctives.npz')).items() if not k.startswith(('JC_Grip', 'JC_MCP'))}
exec(va[va.index('def tent('):va.index('report = {}')])
# Held (persistent) grips only: greedy extra examples from transient reload frames alias other grips on an MCP-only basis.
HELD = {'l': ['/Game/Weapons/M4ContactImpactFinal/A_AKM_idle', '/Game/Weapons/M4VerticalGripVRENatural/Vertical/A_M4_Vertical_idle'], 'r': ['/Game/Weapons/M4ContactImpactFinal/A_AKM_idle']}
MAX_EXAMPLES, SIGMA, MIN_SEPARATION = 2, 12.0, 18.0

ref_mats = {n: (ref_q[n].as_matrix(), ref_t[n]) for n in names}
ix = {n: k for k, n in enumerate(names)}


def frame_data(clip, fi):
    fr = rd['clips'][clip]['frames'][fi]
    t = np.array([b['t'] for b in fr]); q = Rot.from_quat([b['q'] for b in fr])
    Rm = np.zeros((len(bones_used), 3, 3)); Tv = np.zeros((len(bones_used), 3))
    for k, b in enumerate(bones_used):
        j = names.index(b); Mr, tr = ref_mats[b]; Rm[k] = q[j].as_matrix() @ Mr.T; Tv[k] = t[j] - Rm[k] @ tr
    return t, q, Rm, Tv


def mcp_extra(t, s):
    out = []
    for f in ('index', 'middle', 'ring', 'pinky'):
        a = t[ix[f'{f}_01_{s}']] - t[ix[f'{f}_metacarpal_{s}']]; b = t[ix[f'{f}_02_{s}']] - t[ix[f'{f}_01_{s}']]
        out.append(np.degrees(np.arccos(np.clip(a @ b / np.linalg.norm(a) / np.linalg.norm(b), -1, 1))) - meta[f'mcp_{f}_{s}']['rest_deg'])
    return np.maximum(np.array(out), 0)


def total_delta(t, q):
    d = np.zeros_like(P)
    for s in ('l', 'r'):
        w, *_ = drive(t, q, s)
        for n_, x in w.items():
            if x > 1e-4 and n_ in shp: d += shp[n_] * x
    return d


hand_faces = {s: (m.region == 2) & ((P[tw_all].mean(axis=1)[:, 0] < 0) == (s == 'l')) for s in ('l', 'r')}
frames = [(c, fi) for c, v in rd['clips'].items() if not v.get('missing') for fi in range(0, len(v['frames']), 2)]
grips = {}
for s in ('l', 'r'):
    examples = []
    for clip in HELD[s]:
        fi = 0
        t, q, Rm, Tv = frame_data(clip, fi)
        ex = mcp_extra(t, s)
        Xp, A = lbs(P + total_delta(t, q), Rm, Tv)
        mask = ((P[:, 0] < 0) == (s == 'l'))                      # whole arm: the held pose also folds the extended elbow
        corr, g1 = fold_guard(Xp, np.zeros_like(P), mask.astype(float))
        for _ in range(4): corr = .5 * corr + .5 * (Lop @ corr) * mask[:, None]
        corr, g2 = fold_guard(Xp, corr, mask.astype(float))
        rest = np.linalg.solve(A, corr[:, :, None])[:, :, 0]
        mag = np.linalg.norm(rest, axis=1); rest *= np.minimum(1, .5 / np.maximum(mag, 1e-9))[:, None]
        name = 'JC_Grip_%s_%s' % (s.upper(), '_'.join(str(int(round(e))) for e in ex))
        if name in shp: break
        shp[name] = rest; examples.append(ex)
        Xc, _ = lbs(P + total_delta(t, q), Rm, Tv)
        grips[name] = dict(side=s, clip=clip.split('/')[-1], frame=fi, mcp_extra=[int(round(e)) for e in ex], folds_before=g1['folds_lbs_zone'],
                           folds_left_at_example=int(len(inverted(Xc, hand_faces[s]))), vertices=int((mag > .012).sum()), max_rest_cm=float(min(mag.max(), .5)))
        print(name, json.dumps(grips[name]), flush=True)
np.savez(R / 'Work/correctives.npz', **shp)
meta['grips'] = grips; meta['grip_sigma_deg'] = SIGMA
(R / 'Work/correctives.json').write_text(json.dumps(meta, indent=1))





