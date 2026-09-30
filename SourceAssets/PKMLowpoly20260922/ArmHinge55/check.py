"""Joint check of the authored ArmHinge55 split (offline): held-pose upper-arm roll off the
elbow hinge before/after, forearm flips, elbow travel, and clip-boundary consistency with the
matching idle."""
import json, gzip, sys
import numpy as np
from pathlib import Path
from scipy.ndimage import uniform_filter1d
from scipy.spatial.transform import Rotation as R
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import author as A

idx = json.loads((HERE / 'inputs.json').read_text())
rows, bound = [], {}
wrap = lambda x: (x + 180) % 360 - 180
for g in ('PKM', '201'):
    bind = A.Bind(g)
    res = {}
    for key, c in idx[g]['clips'].items():
        with gzip.open(c['file'], 'rt') as f:
            d = json.load(f)
        W = np.array([[A.mat(v) for v in fr] for fr in d['world']])
        out, info = A.solve(W, bind)
        Rh = [A.rot(W[k, A.HA]) for k in range(len(W))]
        hs = np.r_[0, [np.degrees(R.from_matrix(Rh[k] @ Rh[k - 1].T).magnitude()) for k in range(1, len(W))]]
        # held: the source hand keeps its orientation for at least 0.25 s, with the elbow
        # visibly bent (>30 deg; a near-straight elbow has no meaningful hinge roll)
        a_, e_, t_ = W[:, A.UP, :3, 3], W[:, A.LO, :3, 3], W[:, A.HA, :3, 3]
        bend = np.degrees(np.arctan2(np.linalg.norm(np.cross(e_ - a_, t_ - e_), axis=1), np.einsum('ij,ij->i', e_ - a_, t_ - e_)))
        hold = (uniform_filter1d(hs, 31, mode='nearest') < 1.0) & (bend > 30)
        up = np.abs(wrap(info['upper']))
        be = np.abs(wrap(info['before']))
        fl = np.abs(np.diff(info['forearm'])) if len(W) > 1 else np.zeros(1)
        ed = max(np.linalg.norm(o[A.LO][:3, 3] - W[k, A.LO, :3, 3]) for k, o in enumerate(out))
        rows.append(dict(transient_frames=int(((up > 60) & ~hold).sum()), clip=key.split('/Weapons/')[1], held_before=float(be[hold].max()) if hold.any() else 0.,
                         held_after=float(up[hold].max()) if hold.any() else 0., any_after=float(up.max()),
                         forearm_step=float(fl.max()), elbow_cm=float(ed)))
        res[key] = (out[0], out[-1], W[0], W[-1])
    # boundary: first/last frames vs the idle of the same folder/family when the source pose equals it
    for key, (o0, o1, w0, w1) in res.items():
        fam = key.split('/')[-1].split('_')[2] if g == 'PKM' else key.split('/')[-1].split('_')[2]
        idles = [k for k in res if k.endswith('_idle') and (('/%s/' % fam) in k or ('/Animations/A_' in k and '/Animations/A_' in key and '/' not in key.split('/Animations/')[1]))]
        for ik in idles:
            io = res[ik][0]
            for o, w in ((o0, w0), (o1, w1)):
                if np.abs(w[A.HA] - res[ik][2][A.HA]).max() < 1e-3 and np.abs(w[A.UP] - res[ik][2][A.UP]).max() < 1e-3:
                    dev = max(float(np.degrees(R.from_matrix(A.rot(o[i]).T @ A.rot(io[i])).magnitude())) for i in (A.T1, A.T2, A.LO, A.F1, A.F2))
                    bound[key] = max(bound.get(key, 0.), dev)
(HERE / 'check.json').write_text(json.dumps(dict(rows=rows, boundary_deg=bound), indent=1))
rows.sort(key=lambda r: -r['held_after'])
print('clips %d | held upper-arm roll off hinge: before max %.0f, after max %.0f | held after >45: %d, >30: %d' % (
    len(rows), max(r['held_before'] for r in rows), max(r['held_after'] for r in rows),
    sum(r['held_after'] > 45 for r in rows), sum(r['held_after'] > 30 for r in rows)))
print('forearm step >20 deg/frame: %d clips; elbow moved max %.1f cm; idle-boundary mismatch max %.2f deg over %d clip ends' % (
    sum(r['forearm_step'] > 20 for r in rows), max(r['elbow_cm'] for r in rows), max(bound.values()) if bound else 0, len(bound)))
for r in rows[:12]:
    print('  %-64s held %4.0f -> %4.0f | any %4.0f (%d transient frames >60) | elbow %.1f cm' % (
        r['clip'], r['held_before'], r['held_after'], r['any_after'], r['transient_frames'], r['elbow_cm']))
