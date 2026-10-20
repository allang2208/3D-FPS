"""Pose-space corrective shapes for the M4 V9 arms (offline). Writes Work/correctives.npz + correctives.json.

Target at each key pose = Delta Mush of the linear-blend result (rest detail carried in smoothed local
frames), restricted to the joint and pulled back into the reference pose through the blended skinning
rotation, so UE's morph-before-skin reproduces it exactly at the key. Elbow keys add a small olecranon
prominence. Keys follow the joint ranges measured from the shipped M4 clips (Work/pose_ranges.json).
"""
import json
import numpy as np
import scipy.sparse as sp
from scipy.spatial.transform import Rotation as Rot
from m4data import M4, R

m = M4(); wv = m.weld; nw = m.nw
geo = np.load(R / 'Work/geometry.npz'); P = geo['welded']
rd = json.loads((R / 'Snapshot/m4_read.json').read_text()); names = rd['bones']; bi = {n: i for i, n in enumerate(names)}
master_bones = json.loads((R.parent / 'ModularOutfit20260925/BarePalmV7/M4_original.json').read_text())['bones']
by_index = {v['index']: k for k, v in master_bones.items()}
parent = {k: by_index.get(v['parent']) for k, v in master_bones.items()}
children = {k: [] for k in master_bones}
for k, p in parent.items():
    if p: children[p].append(k)
ref_t = {n: np.array(rd['ref_component'][n]['t']) for n in names}
ref_q = {n: Rot.from_quat(rd['ref_component'][n]['q']) for n in names}

# welded weights (first split copy is representative; copies carry identical weights)
W = [None] * nw
for v in range(len(m.X)):
    if W[wv[v]] is None: W[wv[v]] = m.W[v]
for i, row in json.loads((R / 'Work/weights.json').read_text())['changed'].items(): W[int(i)] = row
bones_used = sorted({b for w in W for b in w})
Widx = np.zeros((nw, 8), int); Wval = np.zeros((nw, 8))
for i, w in enumerate(W):
    items = sorted(w.items(), key=lambda x: -x[1])[:8]
    for k, (b, x) in enumerate(items): Widx[i, k] = bones_used.index(b); Wval[i, k] = x
Wval /= Wval.sum(axis=1, keepdims=True)


def descendants(b):
    out = [b]
    for c in children.get(b, []): out += descendants(c)
    return out


def skin_matrices(rotations):
    """rotations: {bone: (Rot, pivot)} applied to the bone and all its descendants (component space)."""
    Rm = np.tile(np.eye(3), (len(bones_used), 1, 1)); Tv = np.zeros((len(bones_used), 3))
    for b, (rot, pivot) in rotations.items():
        M = rot.as_matrix()
        for d in descendants(b):
            if d in bones_used:
                k = bones_used.index(d); Rm[k] = M @ Rm[k]; Tv[k] = M @ Tv[k] + pivot - M @ pivot
    return Rm, Tv


def lbs(X, Rm, Tv):
    A = np.einsum('vk,vkij->vij', Wval, Rm[Widx]); t = np.einsum('vk,vki->vi', Wval, Tv[Widx])
    return np.einsum('vij,vj->vi', A, X) + t, A


# uniform Laplacian smoothing operator on the welded mesh
rows, cols = [], []
for t in wv[m.T]:
    for a in range(3):
        for b in range(3):
            if a != b: rows.append(t[a]); cols.append(t[b])
Adj = sp.coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(nw, nw)).tocsr(); Adj.data[:] = 1
deg = np.asarray(Adj.sum(axis=1)).ravel(); Lop = sp.diags(1 / np.maximum(deg, 1)) @ Adj
ITER = 30


def smooth(X, iters=ITER, lam=.5):
    for _ in range(iters): X = (1 - lam) * X + lam * (Lop @ X)
    return X


def vertex_normals(X):
    tw = wv[m.T]; fn = np.cross(X[tw[:, 1]] - X[tw[:, 0]], X[tw[:, 2]] - X[tw[:, 0]])
    fn *= np.sign(np.einsum('ij,ij->', fn, m.N.mean(axis=1)))
    n = np.zeros_like(X)
    for k in range(3): np.add.at(n, tw[:, k], fn)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


S0 = smooth(P); n0 = vertex_normals(S0)
# tangent neighbour = the one with the longest in-plane edge on the smoothed rest mesh (well conditioned)
tan_nb = np.zeros(nw, int)
for i in range(nw):
    nbs = Adj.indices[Adj.indptr[i]:Adj.indptr[i + 1]]
    if len(nbs) == 0: tan_nb[i] = i; continue
    e = S0[nbs] - S0[i]; e -= np.outer(e @ n0[i], n0[i]); tan_nb[i] = nbs[np.argmax(np.linalg.norm(e, axis=1))]


def frames(X):
    n = vertex_normals(X)
    e = X[tan_nb] - X; e -= np.einsum('ij,ij->i', e, n)[:, None] * n
    t = e / np.maximum(np.linalg.norm(e, axis=1, keepdims=True), 1e-12); b = np.cross(n, t)
    return np.stack([t, b, n], axis=2)                    # columns = t, b, n


F0 = frames(S0); delta = np.einsum('vji,vj->vi', F0, P - S0)


def delta_mush(Xp):
    Sp = smooth(Xp); Fp = frames(Sp); return Sp + np.einsum('vij,vj->vi', Fp, delta)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


tw_all = wv[m.T]


def inverted(X, faces_mask):
    """Faces turned against their own corner normals (pinholes once rendered single-sided)."""
    f = np.cross(X[tw_all[:, 1]] - X[tw_all[:, 0]], X[tw_all[:, 2]] - X[tw_all[:, 0]])
    f *= np.sign(np.einsum('ij,ij->', f, m.N.mean(axis=1)))
    vn = np.zeros_like(X)
    for k in range(3): np.add.at(vn, tw_all[:, k], f)
    vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)
    return np.nonzero((np.einsum('ij,ij->i', f, vn[tw_all].mean(axis=1)) < 0) & faces_mask)[0]


def fold_guard(Xp, corr, mask):
    """Inside the key's zone: untangle every fold (also those plain skinning already makes) by local
    relaxation of the corrected surface; never leave a fold the correction introduced."""
    zone_f = mask[tw_all].max(axis=1) > 0
    before = len(inverted(Xp, zone_f)); it = 0
    for it in range(60):
        Xc = Xp + corr; bad = inverted(Xc, zone_f)
        if not len(bad): break
        vs = set(tw_all[bad].ravel().tolist())
        for _ in range(2 + it // 20): vs |= {int(n) for v in list(vs) for n in Adj.indices[Adj.indptr[v]:Adj.indptr[v + 1]]}
        vs = np.array(sorted(vs)); avg = Lop @ Xc
        corr[vs] += .5 * (avg[vs] - Xc[vs])
    return corr, dict(folds_lbs_zone=int(before), folds_left=int(len(inverted(Xp + corr, zone_f))), guard_iterations=it + 1)


vreg = np.full(nw, -1)
for ti, t in enumerate(m.T):
    for v in t: vreg[wv[v]] = max(vreg[wv[v]], m.region[ti])
finger = np.array([any(f in w and 'metacarpal' not in w for f in ('thumb', 'index', 'middle', 'ring', 'pinky')) for w in
                   [max(W[i], key=W[i].get) for i in range(nw)]])
shapes = {}; meta = {}
for side in ('l', 'r'):
    on = (P[:, 0] < 0) if side == 'l' else (P[:, 0] > 0)
    S_, E_, W_ = ref_t['upperarm_' + side], ref_t['lowerarm_' + side], ref_t['hand_' + side]
    up = (E_ - S_) / np.linalg.norm(E_ - S_); fd = (W_ - E_) / np.linalg.norm(W_ - E_)
    hinge = np.cross(up, fd); hinge /= np.linalg.norm(hinge)
    rest_angle = np.degrees(np.arccos(np.clip(up @ fd, -1, 1)))
    f0 = ref_t['middle_01_' + side] - W_; f0 /= np.linalg.norm(f0)
    r0 = ref_t['index_metacarpal_' + side] - ref_t['pinky_metacarpal_' + side]; r0 -= (r0 @ f0) * f0; r0 /= np.linalg.norm(r0)
    z0 = np.cross(f0, r0)
    # which way is the palm? (dorsal from the accepted palm mask, see geometry_report frame_*)
    dorsal = np.array(json.loads((R / 'Work/geometry_report.json').read_text())['anatomy']['features']['frame_' + side]['dorsal'])
    palm_sign = -1.0 if z0 @ dorsal > 0 else 1.0           # +flex moves the fingers toward the palm
    d_elbow = np.linalg.norm(P - E_, axis=1); d_wrist = np.linalg.norm(P - W_, axis=1)
    mask_e = on * (1 - smoothstep(7.5, 11.5, d_elbow)) * (vreg <= 1)
    mask_w = on * (1 - smoothstep(4.5, 7.0, d_wrist)) * (~finger)
    outer = (up - fd); outer -= (outer @ hinge) * hinge; outer /= np.linalg.norm(outer)
    keys = []
    for ang in (20.0, 75.0, 110.0, 135.0):                     # 20 = the extended elbow of the held rifle poses
        cands = [Rot.from_rotvec(sg * hinge * np.radians(ang - rest_angle)) for sg in (1, -1)]
        rot = min(cands, key=lambda r: abs(np.degrees(np.arccos(np.clip(up @ r.apply(fd), -1, 1))) - ang))
        keys.append(('JC_ElbowFlex%d_%s' % (ang, side.upper()), {'lowerarm_' + side: (rot, E_)}, mask_e, ang))
    # rotvec about r0 by +a moves the fingers toward -z0; about z0 by +a toward +r0 (radial)
    for name, axis, deg in (('JC_WristFlexA_%s', r0, 40.0), ('JC_WristFlexB_%s', r0, -40.0), ('JC_WristRadial_%s', z0, 20.0), ('JC_WristUlnar_%s', z0, -35.0)):
        rot = Rot.from_rotvec(axis * np.radians(deg))
        keys.append((name % side.upper(), {'hand_' + side: (rot, W_)}, mask_w, deg))
    for f in ('index', 'middle', 'ring', 'pinky'):              # bind MCP angles for the grip driver (grip_correctives.py)
        Mc, J1, J2 = ref_t[f'{f}_metacarpal_{side}'], ref_t[f'{f}_01_{side}'], ref_t[f'{f}_02_{side}']
        meta[f'mcp_{f}_{side}'] = dict(rest_deg=float(np.degrees(np.arccos(np.clip((J1 - Mc) @ (J2 - J1) / np.linalg.norm(J1 - Mc) / np.linalg.norm(J2 - J1), -1, 1)))))
    for name, rots, mask, val in keys:
        Rm, Tv = skin_matrices(rots)
        Xp, A = lbs(P, Rm, Tv)
        target = delta_mush(Xp)
        corr = (target - Xp) * mask[:, None]
        if name.startswith('JC_ElbowFlex20'):
            corr = np.zeros_like(P)                               # extension: only untangle what straightening folds
        elif name.startswith('JC_Elbow'):
            # Delta Mush is kept on the stretched outer half and the sides only; inside the crease the
            # two skin sheets meet and smoothing crumples them, so linear blending stays there.
            o_rot = rots['lowerarm_' + side][0]
            bis = outer + o_rot.apply(outer); bis /= np.linalg.norm(bis)
            nposed = vertex_normals(Xp)
            outer_w = smoothstep(-.35, .25, nposed @ bis)
            corr *= outer_w[:, None]
            # crease: plain relaxation of the folded sheet (no detail transport)
            crease = (1 - outer_w) * mask * (1 - smoothstep(4.5, 7.5, np.linalg.norm(Xp - E_, axis=1)))
            relax = smooth(Xp, 16) - Xp; rm = np.linalg.norm(relax, axis=1); relax *= np.minimum(1, .5 / np.maximum(rm, 1e-9))[:, None]
            corr += relax * crease[:, None]
        else:
            # compression side of the bent wrist: relax the folded sheet instead of transporting detail into it
            hand_rot = rots['hand_' + side][0]
            inner = hand_rot.apply(f0) - f0; inner /= np.linalg.norm(inner)
            nposed = vertex_normals(Xp)
            comp = smoothstep(.1, .55, nposed @ inner) * mask * (1 - smoothstep(3.5, 6.0, np.linalg.norm(Xp - W_, axis=1)))
            corr *= (1 - comp)[:, None]
            relax = smooth(Xp, 14) - Xp; rm = np.linalg.norm(relax, axis=1); relax *= np.minimum(1, .3 / np.maximum(rm, 1e-9))[:, None]
            corr += relax * comp[:, None]
        for _ in range(12):                                   # relax the correction field itself (no ridges)
            corr = .5 * corr + .5 * (Lop @ corr) * (mask > 0)[:, None] + .5 * corr * (mask <= 0)[:, None] * 0
        corr *= mask[:, None] > 0
        if name.startswith('JC_Elbow') and val > rest_angle:
            k = (val - rest_angle) / (135 - rest_angle)
            o_rot = rots['lowerarm_' + side][0]
            ol_dir = o_rot.apply(outer) * .5 + outer * .5; ol_dir /= np.linalg.norm(ol_dir)
            centre = E_ + ol_dir * 3.2
            g = np.exp(-(np.linalg.norm(Xp - o_rot.apply(E_ - E_) - centre, axis=1) / 1.6) ** 2) * mask
            nrm = frames(Xp)[:, :, 2]
            corr += nrm * (0.18 * k * g * np.clip(nrm @ ol_dir, 0, 1))[:, None]
        corr, guard = fold_guard(Xp, corr, mask)
        rest = np.linalg.solve(A, corr[:, :, None])[:, :, 0]
        mag = np.linalg.norm(rest, axis=1); rest *= np.minimum(1, 1.2 / np.maximum(mag, 1e-9))[:, None]
        rest[mag < .004] = 0
        # validation at the key: morph-before-skin reproduces the target
        Xc, _ = lbs(P + rest, Rm, Tv)
        tw = wv[m.T]
        def turned(Xa):
            fa = np.cross(Xa[tw[:, 1]] - Xa[tw[:, 0]], Xa[tw[:, 2]] - Xa[tw[:, 0]]); f0_ = np.cross(Xp[tw[:, 1]] - Xp[tw[:, 0]], Xp[tw[:, 2]] - Xp[tw[:, 0]])
            return int((np.einsum('ij,ij->i', fa, f0_) < 0).sum())
        fr = np.cross(P[tw[:, 1]] - P[tw[:, 0]], P[tw[:, 2]] - P[tw[:, 0]])
        in_mask = mask[tw].max(axis=1) > 0
        def folded(Xa):
            fa = np.cross(Xa[tw[:, 1]] - Xa[tw[:, 0]], Xa[tw[:, 2]] - Xa[tw[:, 0]])
            Rr = np.einsum('vk,vkij->vij', Wval, Rm[Widx])[tw[:, 0]]; fr2 = np.einsum('vij,vj->vi', Rr, fr)
            c = np.einsum('ij,ij->i', fa, fr2) / np.maximum(np.linalg.norm(fa, axis=1) * np.linalg.norm(fr2, axis=1), 1e-12)
            return int(((c < 0) & in_mask).sum())
        shapes[name] = rest
        meta[name] = dict(side=side, value=float(val), rest_elbow_deg=float(rest_angle), vertices=int((np.linalg.norm(rest, axis=1) > .015).sum()),
                          max_rest_cm=float(np.linalg.norm(rest, axis=1).max()), max_posed_cm=float(np.linalg.norm(corr, axis=1).max()),
                          folded_lbs=folded(Xp), folded_corrected=folded(Xc), reproduce_err_cm=float(np.abs(Xc - (Xp + corr)).max()), **guard)
        print(name, json.dumps(meta[name]))
    tq = ref_q['lowerarm_twist_01_' + side].inv()
    meta['frame_' + side] = dict(hinge=hinge.tolist(), up=up.tolist(), fd=fd.tolist(), f0=f0.tolist(), r0=r0.tolist(), z0=z0.tolist(),
                                 palm_sign=palm_sign, rest_elbow_deg=float(rest_angle),
                                 # runtime driver: hand->middle_01 in lowerarm_twist_01 space
                                 f0_twist=tq.apply(f0).tolist(), r0_twist=tq.apply(r0).tolist(), z0_twist=tq.apply(z0).tolist(),
                                 flexA_is_palmar=bool(palm_sign < 0))
np.savez(R / 'Work/correctives.npz', **shapes)
(R / 'Work/correctives.json').write_text(json.dumps(meta, indent=1))
