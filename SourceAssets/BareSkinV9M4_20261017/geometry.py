"""V9 M4 rest-shape pass (offline, numpy). Writes Work/geometry.npz + geometry_report.json.

A  wrist ring: bounded Taubin smoothing across the old hand/forearm split, welded normals.
A  sliver relaxation: tangential only, around needle triangles in the hand.
C1 anatomy: forearm cross-section (proximal oval -> flat wrist), ulnar head, olecranon,
   epicondyles, metacarpal heads. Rest-pose displacement only; weights, topology and UVs unchanged.
Every per-vertex displacement is capped at CAP cm and fades to zero away from its feature.
"""
import json
from pathlib import Path
import numpy as np
from m4data import M4, R

CAP = .30
WORK = R / 'Work'; WORK.mkdir(exist_ok=True)
m = M4(); X0 = m.X.copy(); nw = m.nw; wv = m.weld; masks = m.old_masks()
P = np.zeros((nw, 3)); P[wv] = X0
nb = m.welded_adjacency(); vreg_split = m.vertex_region()
vreg = np.full(nw, -1); vreg[wv] = np.maximum(vreg[wv], vreg_split)
for v, r in enumerate(vreg_split): vreg[wv[v]] = max(vreg[wv[v]], r)
J = m.joint


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


def welded_normals(Pw):
    tw = wv[m.T]; fn = np.cross(Pw[tw[:, 1]] - Pw[tw[:, 0]], Pw[tw[:, 2]] - Pw[tw[:, 0]])
    fn *= np.sign(np.einsum('ij,ij->', fn, m.N.mean(axis=1)))
    acc = np.zeros_like(Pw)
    for k in range(3): np.add.at(acc, tw[:, k], fn)
    return acc / np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12)


def laplace(Pw, idx):
    out = Pw.copy()
    for i in idx:
        if nb[i]: out[i] = Pw[list(nb[i])].mean(axis=0)
    return out


report = {}
disp = np.zeros((nw, 3))

# ---- A: wrist ring (old region 1|2 split) ----
def seam(a, b):
    sa = {wv[v] for ti, t in enumerate(m.T) if m.region[ti] == a for v in t}
    return sa & {wv[v] for ti, t in enumerate(m.T) if m.region[ti] == b for v in t}


ring = np.array(sorted(seam(1, 2) | seam(0, 1)))         # old wrist split + V6 upper-arm join above the elbow
from scipy.spatial import cKDTree
dist_ring = cKDTree(P[ring]).query(P)[0]
band = np.nonzero(dist_ring < 1.8)[0]; w_band = 1 - smoothstep(.5, 1.8, dist_ring)
tw = wv[m.T]


def dihedral(Pw, verts):
    """Max dihedral (deg) over edges touching the given welded vertices."""
    fn = np.cross(Pw[tw[:, 1]] - Pw[tw[:, 0]], Pw[tw[:, 2]] - Pw[tw[:, 0]]); fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    vs = set(verts.tolist()); edges = {}
    for ti, t in enumerate(tw):
        for k in range(3):
            a, b = int(t[k]), int(t[(k + 1) % 3])
            if a in vs and b in vs: edges.setdefault((min(a, b), max(a, b)), []).append(ti)
    ang = [np.degrees(np.arccos(np.clip(fn[x[0]] @ fn[x[1]], -1, 1))) for x in edges.values() if len(x) == 2]
    return np.array(ang)


def flips(Pa, Pb):
    fa = np.cross(Pa[tw[:, 1]] - Pa[tw[:, 0]], Pa[tw[:, 2]] - Pa[tw[:, 0]]); fb = np.cross(Pb[tw[:, 1]] - Pb[tw[:, 0]], Pb[tw[:, 2]] - Pb[tw[:, 0]])
    c = np.einsum('ij,ij->i', fa, fb) / np.maximum(np.linalg.norm(fa, axis=1) * np.linalg.norm(fb, axis=1), 1e-12)
    return c


before = dihedral(P, ring)
Q = P.copy()
for _ in range(14):
    for lam in (.45, -.47):
        L = laplace(Q, band) - Q; Q[band] += lam * L[band]
d = (Q - P) * w_band[:, None]
mag = np.linalg.norm(d, axis=1); d *= np.minimum(1, .15 / np.maximum(mag, 1e-9))[:, None]
after = dihedral(P + d, ring)
report['wrist_ring'] = dict(ring_vertices=int(len(ring)), band_vertices=int(len(band)),
                            max_mm=round(float(np.linalg.norm(d, axis=1).max() * 10), 3),
                            ring_dihedral_before=dict(median=round(float(np.median(before)), 2), p90=round(float(np.percentile(before, 90)), 2)),
                            ring_dihedral_after=dict(median=round(float(np.median(after)), 2), p90=round(float(np.percentile(after, 90)), 2)),
                            flipped=int((flips(P, P + d) < 0).sum()))
disp += d

# ---- A: cubital fossa notch (needle triangles left from the old split) ----
fossa_rows = {}
for side in ('l', 'r'):
    S_, E_, W_ = J('upperarm_' + side), J('lowerarm_' + side), J('hand_' + side)
    up = (E_ - S_) / np.linalg.norm(E_ - S_); fd = (W_ - E_) / np.linalg.norm(W_ - E_)
    inner = fd - up; inner /= np.linalg.norm(inner)
    on = (P[:, 0] < 0) if side == 'l' else (P[:, 0] > 0)
    q = P - E_; score = q @ inner - 2.0 * np.linalg.norm(q - np.outer(q @ inner, inner), axis=1)
    k = np.nonzero(on & (vreg <= 1))[0]; c = P[k[np.argmax(score[k])]]
    dist = np.linalg.norm(P - c, axis=1); region = np.nonzero(on & (dist < 4.5))[0]
    wgt = 1 - smoothstep(1.5, 4.5, dist)
    before_f = dihedral(P + disp, region)
    Q = P + disp
    for _ in range(10):
        for lam in (.45, -.47):
            L = laplace(Q, region) - Q; Q[region] += lam * L[region]
    d = (Q - (P + disp)) * wgt[:, None]; mag = np.linalg.norm(d, axis=1); d *= np.minimum(1, .15 / np.maximum(mag, 1e-9))[:, None]
    after_f = dihedral(P + disp + d, region)
    fossa_rows[side] = dict(vertices=int(len(region)), max_mm=round(float(mag.max() * 10 if len(mag) else 0), 3),
                            p99_dihedral_before=round(float(np.percentile(before_f, 99)), 1), p99_dihedral_after=round(float(np.percentile(after_f, 99)), 1),
                            max_dihedral_before=round(float(before_f.max()), 1), max_dihedral_after=round(float(after_f.max()), 1),
                            flipped=int((flips(P + disp, P + disp + d) < 0).sum()))
    disp += d
report['cubital_fossa'] = fossa_rows

# ---- A: micro folds on the arms (needle triangles folded almost flat onto each other near the elbow) ----
Pw = P + disp
fn_ = np.cross(Pw[tw[:, 1]] - Pw[tw[:, 0]], Pw[tw[:, 2]] - Pw[tw[:, 0]]); fn_ /= np.maximum(np.linalg.norm(fn_, axis=1, keepdims=True), 1e-12)
edge_faces = {}
for ti, t in enumerate(tw):
    for k in range(3):
        a, b = int(t[k]), int(t[(k + 1) % 3]); edge_faces.setdefault((min(a, b), max(a, b)), []).append(ti)
core = set()
for (a, b), ts in edge_faces.items():
    if len(ts) == 2 and m.region[ts[0]] <= 1 and m.region[ts[1]] <= 1 and fn_[ts[0]] @ fn_[ts[1]] < np.cos(np.radians(45)): core |= {a, b}
core = np.array(sorted(core)); zone = np.array(sorted(set(core.tolist()) | {n for v in core for n in nb[v]}))
before_fold = dihedral(Pw, zone) if len(zone) else np.zeros(1)
S = Pw.copy()
for _ in range(25):
    L = laplace(S, zone) - S; S[zone] += .5 * L[zone]
d = S - Pw; d[np.setdiff1d(np.arange(nw), zone)] = 0
mag = np.linalg.norm(d, axis=1); d *= np.minimum(1, .12 / np.maximum(mag, 1e-9))[:, None]
after_fold = dihedral(Pw + d, zone) if len(zone) else np.zeros(1)
report['arm_micro_folds'] = dict(core_vertices=int(len(core)), moved=int((mag > 1e-4).sum()), max_mm=round(float(min(mag.max(), .12) * 10), 3),
                                 max_dihedral_before=round(float(before_fold.max()), 1), max_dihedral_after=round(float(after_fold.max()), 1),
                                 flipped=int((flips(Pw, Pw + d) < 0).sum()))
disp += d
micro_zone = set(zone.tolist()) if len(core) else set()

# ---- A: sliver relaxation (tangential, hand) ----
Pw = P + disp
def min_angle(Pw):
    a = Pw[tw]; ang = []
    for k in range(3):
        u = a[:, (k + 1) % 3] - a[:, k]; v = a[:, (k + 2) % 3] - a[:, k]
        c = np.einsum('ij,ij->i', u, v) / np.maximum(np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1), 1e-12)
        ang.append(np.degrees(np.arccos(np.clip(c, -1, 1))))
    return np.min(ang, axis=0)
ma0 = min_angle(Pw)
bad = np.nonzero((ma0 < 3) & (m.region == 2))[0]
move = np.array(sorted({v for t in tw[bad] for v in t}))
nrm = welded_normals(Pw); S = Pw.copy()
for _ in range(6):
    L = laplace(S, move) - S
    L -= np.einsum('ij,ij->i', L, nrm)[:, None] * nrm
    trial = S.copy(); trial[move] += .25 * L[move]
    step = trial - Pw; mag = np.linalg.norm(step, axis=1); trial = Pw + step * np.minimum(1, .06 / np.maximum(mag, 1e-9))[:, None]
    ok = flips(Pw, trial) > .5
    if not ok.all():                                  # undo vertices touching a turned triangle
        undo = {v for t in tw[~ok] for v in t}; trial[list(undo)] = S[list(undo)]
    S = trial
d = S - Pw
ma1 = min_angle(S)
report['slivers'] = dict(triangles=int(len(bad)), moved_vertices=int(len(move)), max_mm=round(float(np.linalg.norm(d, axis=1).max() * 10), 3),
                         min_angle_before=round(float(ma0[bad].min()), 2), min_angle_after=round(float(ma1[bad].min()), 2),
                         still_below_3=int((ma1[bad] < 3).sum()), flipped=int((flips(Pw, S) < 0).sum()))
disp += d

# ---- C1: anatomy, per side ----
nrm = welded_normals(P + disp)
feat = np.zeros((nw, 3)); feature_rows = {}


def bump(centre, normal_dir, height, radius, mask, stretch_axis=None, stretch=1.0, name=''):
    q = P - centre
    if stretch_axis is not None:
        along = q @ stretch_axis; q = q - np.outer(along, stretch_axis) + np.outer(along / stretch, stretch_axis)
    r = np.linalg.norm(q, axis=1)
    f = np.exp(-(r / radius) ** 2 * 2.0) * mask * np.clip(nrm @ normal_dir, 0, 1) ** .5
    feat[:] += nrm * (height * f)[:, None]
    feature_rows[name] = dict(height_mm=height * 10, radius_cm=radius, vertices=int((f > .05).sum()))


for side, sgn in (('l', -1), ('r', 1)):
    S_, E_, W_ = J('upperarm_' + side), J('lowerarm_' + side), J('hand_' + side)
    up = (E_ - S_) / np.linalg.norm(E_ - S_); fd = (W_ - E_) / np.linalg.norm(W_ - E_); Lf = np.linalg.norm(W_ - E_)
    hinge = np.cross(up, fd); hinge /= np.linalg.norm(hinge)
    if hinge[0] * sgn > 0: hinge = -hinge                      # medial = toward the body midline
    radial = J('index_metacarpal_' + side) - J('pinky_metacarpal_' + side)
    on_side = (P[:, 0] < 0) if side == 'l' else (P[:, 0] > 0)
    # Dorsal = opposite of the accepted palmar-skin mask, measured on the metacarpal body only.
    tri_side = (m.X[m.T].mean(axis=1)[:, 0] < 0) == (side == 'l')
    palm_tris = np.nonzero(tri_side & (masks[:, 3] > .6) & np.array([m.dominant[t[0]].startswith('hand') for t in m.T]))[0]
    fn_p = np.cross(m.X[m.T[palm_tris, 1]] - m.X[m.T[palm_tris, 0]], m.X[m.T[palm_tris, 2]] - m.X[m.T[palm_tris, 0]])
    fn_p *= np.sign(np.einsum('ij,ij->', fn_p, m.N[palm_tris].mean(axis=1)))
    dorsal = -fn_p.sum(axis=0); dorsal -= (dorsal @ radial) / (radial @ radial) * radial; dorsal /= np.linalg.norm(dorsal)
    arm = on_side & (vreg <= 1); hand = on_side & (vreg == 2)
    # Forearm cross-section: area-preserving ellipse toward a tapering target ratio.
    s = (P - E_) @ fd / Lf
    def perp(v):
        v = v - (v @ fd) * fd; return v / np.linalg.norm(v)
    m_prox = perp(hinge); r_w = perp(radial)
    if r_w @ m_prox < 0: r_w = -r_w
    total = np.arccos(np.clip(m_prox @ r_w, -1, 1)); axis_sign = np.sign(np.cross(m_prox, r_w) @ fd) or 1
    sel = np.nonzero((on_side) & (vreg <= 2) & (s > .05) & (s < 1.0))[0]
    sel = sel[np.linalg.norm((P[sel] - E_) - np.outer((P[sel] - E_) @ fd, fd), axis=1) < 7.5]
    # slice centroids along s (smoothed)
    bins = np.linspace(0, 1, 41); cent = []
    for a, b in zip(bins[:-1], bins[1:]):
        k = sel[(s[sel] >= a) & (s[sel] < b) & (vreg[sel] <= 1)]
        cent.append(P[k].mean(axis=0) - (E_ + fd * Lf * (a + b) / 2) if len(k) > 20 else np.zeros(3))
    cent = np.array(cent)
    for _ in range(3): cent[1:-1] = (cent[:-2] + 2 * cent[1:-1] + cent[2:]) / 4
    sc = (bins[:-1] + bins[1:]) / 2
    target = np.interp(s, [0, .2, .4, .6, .75, .88, .97, 1.05], [1.08, 1.12, 1.15, 1.18, 1.24, 1.34, 1.45, 1.5])
    # rotation of the wide axis from the epicondyles to the radio-ulnar wrist axis, mostly in the distal half
    rot = total * smoothstep(.15, .95, s) * axis_sign
    measured = {}
    for a, b in zip(np.linspace(.05, .95, 10)[:-1], np.linspace(.05, .95, 10)[1:]):
        k = sel[(s[sel] >= a) & (s[sel] < b) & (vreg[sel] <= 1)]
        if len(k) < 30: continue
        c0 = np.interp((a + b) / 2, sc, cent[:, 0]), np.interp((a + b) / 2, sc, cent[:, 1]), np.interp((a + b) / 2, sc, cent[:, 2])
        rr = rot[k].mean(); mdir = m_prox * np.cos(rr) + np.cross(fd, m_prox) * np.sin(rr); ndir = np.cross(fd, mdir)
        q = P[k] - E_ - np.outer(s[k] * Lf, fd) - np.array(c0)
        measured[round((a + b) / 2, 2)] = float(np.ptp(q @ mdir) / np.ptp(q @ ndir))
    ms = np.array(sorted(measured)); mv = np.array([measured[x] for x in ms])
    current = np.interp(s, ms, mv)
    w_fore = smoothstep(.17, .32, s) * (1 - smoothstep(.9, 1.0, s)) * (vreg <= 1)
    for i in sel:
        if w_fore[i] <= 0: continue
        c = E_ + fd * (s[i] * Lf) + np.array([np.interp(s[i], sc, cent[:, j]) for j in range(3)])
        rr = rot[i]; mdir = m_prox * np.cos(rr) + np.cross(fd, m_prox) * np.sin(rr); ndir = np.cross(fd, mdir)
        q = P[i] - c; u_, v_ = q @ mdir, q @ ndir
        k = np.sqrt(max(target[i], 1) / max(current[i], .8))
        k = np.clip(k, .9, 1.12)
        slim = 1 - .03 * smoothstep(.12, .25, s[i]) * (1 - smoothstep(.38, .55, s[i]))
        new = c + (q - u_ * mdir - v_ * ndir) + mdir * u_ * k * slim + ndir * v_ / k * slim
        feat[i] += (new - P[i]) * w_fore[i]
    feature_rows['forearm_' + side] = dict(ratio_before={str(k): round(v, 3) for k, v in measured.items()},
                                           rotation_deg=round(float(np.degrees(total)), 1))
    # Bony landmarks (outward along the normal, soft Gaussian, single-sided).
    ulnar = perp(J('pinky_metacarpal_' + side) - J('index_metacarpal_' + side))
    feature_rows['frame_' + side] = dict(dorsal=dorsal.round(3).tolist(), ulnar=ulnar.round(3).tolist(), medial=hinge.round(3).tolist(),
                                         palm_triangles=int(len(palm_tris)))
    def surface_point(base, direction, mask):
        k = np.nonzero(mask)[0]; q = P[k] - base
        score = (q @ direction) - 2.5 * np.linalg.norm(q - np.outer(q @ direction, direction), axis=1)
        return P[k[np.argmax(score)]]
    near_wrist = on_side & (np.abs(s - (1 - 1.3 / Lf)) < .04) & (vreg <= 2)
    us = surface_point(W_ - fd * 1.3, perp(.75 * ulnar + .66 * dorsal), near_wrist)
    bump(us, perp(.75 * ulnar + .66 * dorsal), .22, .75, on_side.astype(float), fd, 1.3, 'ulnar_head_' + side)
    rs = surface_point(W_ - fd * .9, perp(-ulnar * .9 + dorsal * .3), on_side & (np.abs(s - (1 - .9 / Lf)) < .04) & (vreg <= 2))
    bump(rs, perp(-ulnar * .9 + dorsal * .3), .08, .6, on_side.astype(float), fd, 1.3, 'radial_styloid_' + side)
    outer = perp(up - fd); outer = outer - (outer @ hinge) * hinge; outer /= np.linalg.norm(outer)
    near_elbow = on_side & (np.linalg.norm(P - E_, axis=1) < 6) & (vreg <= 1)
    ol = surface_point(E_ + fd * .6, outer, near_elbow)
    bump(ol, outer, .22, 1.25, on_side.astype(float), fd, 1.25, 'olecranon_' + side)
    me = surface_point(E_, hinge, near_elbow); bump(me, hinge, .18, .9, on_side.astype(float), None, 1, 'medial_epicondyle_' + side)
    le = surface_point(E_, -hinge, near_elbow); bump(le, -hinge, .08, .8, on_side.astype(float), None, 1, 'lateral_epicondyle_' + side)
    for f in ('index', 'middle', 'ring', 'pinky'):
        head = J(f'{f}_01_{side}'); dirn = dorsal
        knuckle_mask = (hand & (np.linalg.norm(P - head, axis=1) < 2.0)).astype(float)
        pk = surface_point(head, dirn, knuckle_mask > 0)
        bump(pk, dirn, .11 if f != 'pinky' else .08, .55, knuckle_mask, None, 1, f'mcp_{f}_{side}')

# cap and combine
mag = np.linalg.norm(feat, axis=1); scale = np.minimum(1, CAP / np.maximum(mag, 1e-9)); feat *= scale[:, None]
# light smoothing of the displacement field itself keeps the reshape free of per-vertex ripples
idx = np.nonzero(np.linalg.norm(feat, axis=1) > 1e-5)[0]; idx = np.array(sorted(set(idx) | {n for i in idx for n in nb[i]}))
for _ in range(4):
    sm = feat.copy()
    for i in idx: sm[i] = .5 * feat[i] + .5 * feat[list(nb[i])].mean(axis=0)
    feat = sm
report['anatomy'] = dict(features=feature_rows, max_mm=round(float(np.linalg.norm(feat, axis=1).max() * 10), 3),
                         moved_over_0p2mm=int((np.linalg.norm(feat, axis=1) > .02).sum()),
                         flipped=int((flips(P + disp, P + disp + feat) < 0).sum()))
disp += feat
P1 = P + disp


# ---- A: geometric fold-overs (winding is consistent, but the sheet is folded back: shows as a pinhole) ----
def against_normals(X):
    f = np.cross(X[tw[:, 1]] - X[tw[:, 0]], X[tw[:, 2]] - X[tw[:, 0]]); f *= np.sign(np.einsum('ij,ij->', f, m.N.mean(axis=1)))
    vn_ = np.zeros_like(X)
    for k in range(3): np.add.at(vn_, tw[:, k], f)
    vn_ /= np.maximum(np.linalg.norm(vn_, axis=1, keepdims=True), 1e-12)
    return np.nonzero(np.einsum('ij,ij->i', f, vn_[tw].mean(axis=1)) < 0)[0]


bad0 = against_normals(P1); untangle = set()
if len(bad0):
    core = {v for t in tw[bad0] for v in t}
    zone = set(core)
    for _ in range(2): zone |= {n for v in list(zone) for n in nb[v]}
    zone = np.array(sorted(zone)); Q = P1.copy()
    for it in range(60):
        L = laplace(Q, zone) - Q; Q[zone] += .5 * L[zone]
        step = Q - P1; mag = np.linalg.norm(step, axis=1); Q = P1 + step * np.minimum(1, .15 / np.maximum(mag, 1e-9))[:, None]
        if not len(against_normals(Q)): break
    untangle = set(zone.tolist())
    report['fold_overs'] = dict(faces_before=int(len(bad0)), faces_after=int(len(against_normals(Q))), iterations=it + 1,
                                moved=int((np.linalg.norm(Q - P1, axis=1) > 1e-4).sum()), max_mm=round(float(np.linalg.norm(Q - P1, axis=1).max() * 10), 3),
                                where=sorted({max(m.W[np.nonzero(wv == v)[0][0]], key=m.W[np.nonzero(wv == v)[0][0]].get) for v in core}))
    disp += Q - P1; P1 = Q

# flips / quality in rest pose
fn0 = np.cross(P[tw[:, 1]] - P[tw[:, 0]], P[tw[:, 2]] - P[tw[:, 0]]); fn1 = np.cross(P1[tw[:, 1]] - P1[tw[:, 0]], P1[tw[:, 2]] - P1[tw[:, 0]])
cosf = np.einsum('ij,ij->i', fn0, fn1) / np.maximum(np.linalg.norm(fn0, axis=1) * np.linalg.norm(fn1, axis=1), 1e-12)
report['rest_quality'] = dict(flipped=int((cosf < 0).sum()), turned_over_30deg=int((cosf < np.cos(np.radians(30))).sum()),
                              max_disp_mm=round(float(np.linalg.norm(disp, axis=1).max() * 10), 3))
np.savez(WORK / 'geometry.npz', welded=P1, disp=disp, weld=wv, refit=np.array(sorted(untangle | micro_zone), int))
(WORK / 'geometry_report.json').write_text(json.dumps(report, indent=1))
print(json.dumps(report, indent=1))


