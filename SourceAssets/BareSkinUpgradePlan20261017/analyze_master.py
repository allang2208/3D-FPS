"""Read-only geometry/shading audit of the accepted V7/V8 bare-arm master.

Input: SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json (UE cm, UE winding).
Output: master_audit.json (+ console summary). Nothing is written back.
"""
import json, math, collections
from pathlib import Path
import numpy as np

P = Path('D:/FPS3D/FPSGAME'); OUT = P / 'SourceAssets/BareSkinUpgradePlan20261017'
d = json.loads((P / 'SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json').read_text())
X = np.array(d['positions']); T = np.array(d['triangles']); CN = np.array(d['normals']); UV = np.array(d['uv'])
TM = np.array(d['triangle_materials']); B = d['bones']; W = d['weights']
J = {k: np.array(v['position']) for k, v in B.items()}
dominant = [max(w, key=w.get) if w else '' for w in W]

fn = np.cross(X[T[:, 1]] - X[T[:, 0]], X[T[:, 2]] - X[T[:, 0]])
area = np.linalg.norm(fn, axis=1) / 2
sign = np.sign(np.einsum('ij,ij->', fn, CN.mean(axis=1)))
fn_unit = sign * fn / np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
vn = np.zeros_like(X)
for k in range(3): np.add.at(vn, T[:, k], fn_unit * area[:, None])
vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)


def ang(a, b): return np.degrees(np.arccos(np.clip(np.einsum('...i,...i->...', a, b), -1, 1)))


def region_of_vertex(i):
    b = dominant[i]
    if any(s in b for s in ('thumb', 'index', 'middle', 'ring', 'pinky')):
        return 'fingers' if 'metacarpal' not in b else 'palm'
    if b.startswith('hand'): return 'palm'
    p = X[i]; side = 'l' if p[0] < 0 else 'r'
    E, Wr = J['lowerarm_' + side], J['hand_' + side]
    if np.linalg.norm(p - Wr) < 4.0: return 'wrist'
    if np.linalg.norm(p - E) < 6.0: return 'elbow'
    if 'lowerarm' in b: return 'forearm'
    return 'upperarm'


vreg = [region_of_vertex(i) for i in range(len(X))]
treg = [collections.Counter(vreg[v] for v in t).most_common(1)[0][0] for t in T]

# 1. Stored corner normals vs geometric smooth normals.
dev = ang(CN, vn[T])
corner_dev = collections.defaultdict(lambda: [0, 0, 0, 0])
for ti in range(len(T)):
    for k in range(3):
        r = corner_dev[treg[ti]]; r[0] += 1; a = dev[ti, k]
        r[1] += a > 5; r[2] += a > 10; r[3] += a > 20

# 2. Hard shading edges and UV0 seams.
edges = collections.defaultdict(list)
for ti, t in enumerate(T):
    for k in range(3):
        a, b = int(t[k]), int(t[(k + 1) % 3]); edges[(min(a, b), max(a, b))].append((ti, k, (k + 1) % 3) if a < b else (ti, (k + 1) % 3, k))
hard = collections.defaultdict(lambda: [0, 0.0]); seam = collections.defaultdict(lambda: [0, 0.0])
mat_boundary = []; open_edges = 0
for (a, b), uses in edges.items():
    if len(uses) != 2: open_edges += len(uses) == 1; continue
    (t1, a1, b1), (t2, a2, b2) = uses
    L = float(np.linalg.norm(X[a] - X[b])); r = treg[t1]
    h = max(ang(CN[t1, a1], CN[t2, a2]), ang(CN[t1, b1], CN[t2, b2]))
    if h > 5: hard[r][0] += 1; hard[r][1] += L
    if np.abs(UV[t1, a1] - UV[t2, a2]).max() > 1e-5 or np.abs(UV[t1, b1] - UV[t2, b2]).max() > 1e-5:
        seam[r][0] += 1; seam[r][1] += L
    if TM[t1] != TM[t2]: mat_boundary.append((a, b, int(TM[t1]), int(TM[t2]), float(h)))

# 3. UV0 texel density (4096 atlas) per region.
uvA = np.abs(np.cross(UV[:, 1] - UV[:, 0], UV[:, 2] - UV[:, 0])) / 2 * 4096 ** 2
dens = np.sqrt(uvA / np.maximum(area, 1e-9))
density = {}
for r in sorted(set(treg)):
    m = np.array([x == r for x in treg]) & (area > 1e-4)
    density[r] = dict(median=float(np.median(dens[m])), p10=float(np.percentile(dens[m], 10)), p90=float(np.percentile(dens[m], 90)))

# 4. Cross-sections along the left forearm and upper arm.
def hull(pts):
    pts = sorted(map(tuple, pts))
    if len(pts) < 3: return pts
    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0]) <= 0: h.pop()
            h.append(p)
        return h
    lo, up = half(pts), half(reversed(pts)); return lo[:-1] + up[:-1]


def sections(A, Bp, t_values, radius, tag):
    axis = Bp - A; length = np.linalg.norm(axis); axis /= length
    ref = np.array([0, 0, 1.0]) if abs(axis[2]) < .9 else np.array([1.0, 0, 0])
    e1 = np.cross(axis, ref); e1 /= np.linalg.norm(e1); e2 = np.cross(axis, e1)
    s = (X - A) @ axis
    rows = []
    for t in t_values:
        c = t * length; d0 = s[T] - c
        cross = (d0.min(axis=1) < 0) & (d0.max(axis=1) > 0)
        pts = []
        for ti in np.nonzero(cross)[0]:
            for k in range(3):
                i, j = T[ti, k], T[ti, (k + 1) % 3]
                if (d0[ti, k] < 0) != (d0[ti, (k + 1) % 3] < 0):
                    f = d0[ti, k] / (d0[ti, k] - d0[ti, (k + 1) % 3]); p = X[i] + f * (X[j] - X[i])
                    q = p - A - axis * c
                    if np.linalg.norm(q) < radius: pts.append([q @ e1, q @ e2])
        if len(pts) < 12: continue
        pts = np.array(pts); ctr = pts.mean(axis=0); Q = pts - ctr
        w, v = np.linalg.eigh(np.cov(Q.T)); major, minor = Q @ v[:, 1], Q @ v[:, 0]
        h = np.array(hull(pts)); per = float(np.sum(np.linalg.norm(np.roll(h, -1, axis=0) - h, axis=1)))
        th = np.arctan2(minor, major); rr = np.hypot(major, minor)
        M = np.stack([np.ones_like(th)] + [f(n * th) for n in range(1, 5) for f in (np.cos, np.sin)], 1)
        coef, *_ = np.linalg.lstsq(M, rr, rcond=None); res = rr - M @ coef
        rows.append(dict(t=round(float(t), 3), cm_from_start=round(float(c), 2), width=round(float(np.ptp(major)), 2),
                         depth=round(float(np.ptp(minor)), 2), ratio=round(float(np.ptp(major) / max(np.ptp(minor), 1e-6)), 2),
                         hull_perimeter=round(per, 2), bump_rms_mm=round(float(np.sqrt(np.mean(res ** 2)) * 10), 2),
                         bump_max_mm=round(float(np.abs(res).max() * 10), 2), points=len(pts)))
    print(tag, 'length %.1f cm' % length)
    for r in rows: print('  t=%5.3f %5.1fcm  w %5.2f d %5.2f ratio %4.2f  perim %5.2f  bump rms %.2f max %.2f mm' % (
        r['t'], r['cm_from_start'], r['width'], r['depth'], r['ratio'], r['hull_perimeter'], r['bump_rms_mm'], r['bump_max_mm']))
    return dict(length_cm=float(length), rows=rows)


forearm = sections(J['lowerarm_l'], J['hand_l'], np.arange(-.10, 1.06, .04), 7.0, 'FOREARM_L (elbow->wrist)')
upper = sections(J['upperarm_l'], J['lowerarm_l'], np.arange(.15, 1.08, .05), 8.5, 'UPPERARM_L (shoulder->elbow)')

# 5. Material section boundaries relative to the wrist and elbow joints.
mb = collections.defaultdict(list)
for a, b, m1, m2, h in mat_boundary:
    p = (X[a] + X[b]) / 2; side = 'l' if p[0] < 0 else 'r'
    ax = J['hand_' + side] - J['lowerarm_' + side]; L = np.linalg.norm(ax); ax /= L
    mb[tuple(sorted((m1, m2)))].append((float((p - J['hand_' + side]) @ ax), h))
boundary = {f'{k[0]}|{k[1]}': dict(edges=len(v), along_from_wrist_cm=[round(min(x for x, _ in v), 2), round(max(x for x, _ in v), 2)],
                                     normal_break_deg_max=round(max(h for _, h in v), 1), normal_break_deg_mean=round(float(np.mean([h for _, h in v])), 1))
            for k, v in mb.items()}
mat_regions = {int(m): collections.Counter(treg[i] for i in np.nonzero(TM == m)[0]).most_common() for m in sorted(set(TM))}

result = dict(vertices=len(X), triangles=len(T), open_edges=open_edges,
              corner_normal_deviation={r: dict(corners=v[0], over5=v[1], over10=v[2], over20=v[3]) for r, v in corner_dev.items()},
              hard_shading_edges_over5deg={r: dict(edges=v[0], length_cm=round(v[1], 1)) for r, v in hard.items()},
              uv0_seams={r: dict(edges=v[0], length_cm=round(v[1], 1)) for r, v in seam.items()},
              uv0_texels_per_cm_4096=density, material_boundaries=boundary, material_regions=mat_regions,
              forearm_left=forearm, upperarm_left=upper)
plain = lambda o: o.item() if hasattr(o, 'item') else str(o)
(OUT / 'master_audit.json').write_text(json.dumps(result, indent=1, default=plain))
for k in ('open_edges', 'corner_normal_deviation', 'hard_shading_edges_over5deg', 'uv0_seams', 'uv0_texels_per_cm_4096', 'material_boundaries', 'material_regions'):
    print(k, json.dumps(result[k], default=plain))
