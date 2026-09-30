"""Item 1: denoise the Meshy-generated surfaces of A762 (plain CPython, numpy/scipy).

The Meshy receiver, rear grip and bolt are lumpy (about 0.27 mm bumps, ~20 deg normal
wobble within 3.5 mm) while the rebuilt parts are flat; satin metal turns the lumps into
crawling highlights. The atlas normal map is mild (median tilt 0.3 deg), so the lumps are in
the geometry.

Method (bilateral mesh denoising): face normals are filtered with a spatial x normal-range
kernel, then vertices are moved to agree with the filtered normals (capped at MAX_MOVE,
silhouette-preserving), and corner normals are rebuilt per vertex from clusters of the
filtered face normals (a crease splits clusters, so every face of a smooth region shares
one normal at a vertex). Only nominally smooth panels are filtered: faces whose 4.5 mm
neighbourhood already spreads more than FEATURE_DEG (selector, pins, levers, detents) keep
their original normals, with a soft transition, and the effect fades to zero over BORDER_FADE
towards open borders and seams with other slots, whose vertices stay put. Each slot is bound
to a single bone, so bind space is fine.

Writes Bake/denoise_plan.bin (header line JSON + raw arrays) and Bake/denoise_report.json.
"""
import json
import sys
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import seated  # noqa: E402

KEY = 'A762_AfterRepair'
SLOTS = ('M_A762_Receiver', 'M_A762_FactoryRearGrip', 'M_A762_Bolt')
# The lumps wobble the normal by ~20 deg over 2-5 mm, so the range kernel must pass that
# while real machined edges (> ~45 deg) stay separated.
# Geometry moves are capped small (the lumps span several mm, fitting them fully would drift
# the surface); the shading comes from the filtered normals.
RADIUS, SIGMA_S, SIGMA_R, NORMAL_ITERS = 0.45, 0.2, 0.6, 8
VERTEX_ITERS, MAX_MOVE, CREASE_DEG = 12, 0.03, 40.0
FEATURE_DEG, FEATURE_SOFT, BORDER_FADE = 24.0, 8.0, 0.4
QUICK = '--quick' in sys.argv

h, pos, st, tri, mat, bone, gun = seated.load(KEY)
_, _, _, _, _, nrm = seated.read_geometry(seated.GEOMETRY / (KEY + '.bin'))
slot_ids = [h['slots'].index(s) for s in SLOTS]
sel = np.nonzero(np.isin(mat, slot_ids))[0]
T = tri[sel]
V = pos.astype(np.float64).copy()


def face_data(P):
    a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    cr = np.cross(b - a, c - a)
    area = 0.5 * np.linalg.norm(cr, axis=1)
    n = cr / np.maximum(2 * area, 1e-12)[:, None]
    return n, area, (a + b + c) / 3.0


def local_metrics(P, n, area, cent, samples=4000):
    """Median area-weighted normal spread and plane residual within 3.5 mm on non-edge patches."""
    tree = cKDTree(cent)
    rng = np.random.default_rng(3)
    ang, res = [], []
    for i in rng.choice(len(cent), min(samples, len(cent)), replace=False):
        nb = tree.query_ball_point(cent[i], 0.35)
        if len(nb) < 6:
            continue
        nb = np.array(nb)
        nb = nb[n[nb] @ n[i] > 0]
        w = area[nb]
        m = (n[nb] * w[:, None]).sum(0)
        m /= np.linalg.norm(m)
        a = np.degrees(np.arccos(np.clip(n[nb] @ m, -1, 1)))
        if np.average(a, weights=w) > 25:
            continue
        ang.append(np.average(a, weights=w))
        c0 = (cent[nb] * w[:, None]).sum(0) / w.sum()
        res.append(np.sqrt(np.average(((cent[nb] - c0) @ m) ** 2, weights=w)) * 10)
    return {'normal_spread_deg_median': round(float(np.median(ang)), 2),
            'plane_residual_mm_median': round(float(np.median(res)), 4)}


def sharp_edges(n):
    """Share of interior edges whose faces meet at more than 45 deg (feature preservation)."""
    ekey = np.sort(np.stack([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]], 1).reshape(-1, 2), axis=1)
    k = ekey[:, 0].astype(np.int64) * len(V) + ekey[:, 1]
    face = np.repeat(np.arange(len(T)), 3)
    o = np.argsort(k, kind='stable')
    ks, fs = k[o], face[o]
    pair = np.nonzero(ks[1:] == ks[:-1])[0]
    d = np.abs(np.einsum('ij,ij->i', n[fs[pair]], n[fs[pair + 1]]))
    return round(float((d < np.cos(np.radians(45))).mean()), 4)


n0, area0, cent0 = face_data(V)
before = local_metrics(V, n0, area0, cent0)
before['sharp_edge_share'] = sharp_edges(n0)

# Frozen vertices: open borders of the submesh and vertices also used by other slots.
E = np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), axis=1)
_, inv, cnt = np.unique(E[:, 0].astype(np.int64) * len(V) + E[:, 1], return_inverse=True, return_counts=True)
frozen = np.zeros(len(V), bool)
frozen[E[cnt[inv] != 2].ravel()] = True
frozen[np.intersect1d(np.unique(T), np.unique(tri[~np.isin(mat, slot_ids)]))] = True

# Bilateral face-normal filtering (faces facing away from each other never mix).
tree = cKDTree(cent0)
neigh = tree.query_ball_point(cent0, RADIUS)
lens = np.array([len(x) for x in neigh])
rows = np.repeat(np.arange(len(T)), lens)
cols = np.concatenate([np.asarray(x, dtype=np.int64) for x in neigh])
ws = np.exp(-np.sum((cent0[rows] - cent0[cols]) ** 2, 1) / (2 * SIGMA_S ** 2)) * area0[cols]
n = n0.copy()
for _ in range(NORMAL_ITERS):
    d = np.linalg.norm(n[rows] - n[cols], axis=1)
    w = ws * np.exp(-d ** 2 / (2 * SIGMA_R ** 2)) * (np.einsum('ij,ij->i', n[rows], n[cols]) > 0)
    acc = np.zeros_like(n)
    np.add.at(acc, rows, n[cols] * w[:, None])
    n = acc / np.maximum(np.linalg.norm(acc, axis=1), 1e-12)[:, None]

# Where to apply: smooth panels only (original neighbourhood spread below FEATURE_DEG),
# fading out towards frozen borders and seams.
same = np.einsum('ij,ij->i', n0[rows], n0[cols]) > 0
wa = area0[cols] * same
mean_n = np.zeros_like(n0)
np.add.at(mean_n, rows, n0[cols] * wa[:, None])
mean_n /= np.maximum(np.linalg.norm(mean_n, axis=1), 1e-12)[:, None]
pair_ang = np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i', n0[cols], mean_n[rows]), -1, 1)))
spread = np.bincount(rows, pair_ang * wa, len(T)) / np.maximum(np.bincount(rows, wa, len(T)), 1e-12)
m_feature = np.clip((FEATURE_DEG + FEATURE_SOFT / 2 - spread) / FEATURE_SOFT, 0, 1)
used_frozen = np.nonzero(frozen)[0]
d_border = cKDTree(V[used_frozen]).query(cent0)[0] if len(used_frozen) else np.full(len(T), 1e9)
strength = m_feature * np.clip(d_border / BORDER_FADE, 0, 1)
n = n0 + strength[:, None] * (n - n0)
n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]

# Vertex update towards the blended normals (Sun et al.), capped displacement.
vf_rows = T.ravel()
vf_face = np.repeat(np.arange(len(T)), 3)
count = np.bincount(vf_rows, minlength=len(V)).astype(np.float64)
v_strength = np.bincount(vf_rows, strength[vf_face], len(V)) / np.maximum(count, 1)
movable = (count > 0) & ~frozen
P = V.copy()
for _ in range(VERTEX_ITERS):
    _, _, cent = face_data(P)
    proj = np.einsum('ij,ij->i', n[vf_face], cent[vf_face] - P[vf_rows])
    delta = np.zeros_like(P)
    np.add.at(delta, vf_rows, n[vf_face] * proj[:, None])
    delta /= np.maximum(count, 1)[:, None]
    P[movable] += delta[movable] * v_strength[movable, None]
    off = P - V
    dist = np.linalg.norm(off, axis=1)
    over = dist > MAX_MOVE
    P[over] = V[over] + off[over] * (MAX_MOVE / dist[over])[:, None]

n1, area1, cent1 = face_data(P)
after_geometry = local_metrics(P, n1, area1, cent1)
after_geometry['sharp_edge_share'] = sharp_edges(n1)
if QUICK:
    print('A762_DENOISE_QUICK', json.dumps({'before': before, 'after_geometry': after_geometry,
          'filtered': local_metrics(P, n, area1, cent1), 'max_move_mm': round(float(np.linalg.norm(P - V, axis=1).max() * 10), 3),
          'p90_move_mm': round(float(np.percentile(np.linalg.norm(P - V, axis=1)[movable], 90) * 10), 3)}), flush=True)
    sys.exit(0)

# Corner normals: per vertex, cluster the incident faces by blended normal (a crease splits
# clusters) so all faces of a smooth region share one normal there; then blend with the
# original corner normal by the vertex strength, keeping each original corner's orientation
# (Meshy has some inward-wound faces).
cos_c = np.cos(np.radians(CREASE_DEG))
orig = nrm[sel].astype(np.float64)
orig /= np.maximum(np.linalg.norm(orig, axis=2, keepdims=True), 1e-12)
corner = orig.copy()
where = {}
for fi in range(len(T)):
    for k in range(3):
        where.setdefault(T[fi, k], []).append((fi, k))
for v, members in where.items():
    s = v_strength[v]
    if s <= 0:
        continue
    members.sort(key=lambda fk: -area1[fk[0]])
    clusters = []  # [sum vector, unit normal]
    assign = []
    for fi, k in members:
        nf = n[fi]
        for ci, (acc, unit) in enumerate(clusters):
            d = nf @ unit
            if abs(d) >= cos_c:
                acc += nf * np.sign(d) * area1[fi]
                clusters[ci][1] = acc / max(np.linalg.norm(acc), 1e-12)
                assign.append((fi, k, ci, np.sign(d)))
                break
        else:
            clusters.append([nf * area1[fi], nf.copy()])
            assign.append((fi, k, len(clusters) - 1, 1.0))
    for fi, k, ci, sg in assign:
        target = clusters[ci][1] * sg
        o = orig[fi, k]
        if target @ o < 0:
            target = -target
        c = o * (1 - s) + target * s
        corner[fi, k] = c / max(np.linalg.norm(c), 1e-12)

moved = np.nonzero(np.linalg.norm(P - V, axis=1) > 1e-5)[0]
report = {'key': KEY, 'slots': SLOTS, 'triangles': int(len(sel)), 'frozen_vertices': int(frozen[np.unique(T)].sum()),
          'moved_vertices': int(len(moved)), 'max_move_mm': round(float(np.linalg.norm(P - V, axis=1).max() * 10), 3),
          'mean_move_mm': round(float(np.linalg.norm(P - V, axis=1)[moved].mean() * 10), 4) if len(moved) else 0,
          'before': before, 'after_geometry': after_geometry,
          'filtered_normals': local_metrics(P, n, area1, cent1),
          'face_share_filtered': round(float((strength > 0.5).mean()), 3),
          'params': {'radius_cm': RADIUS, 'sigma_s_cm': SIGMA_S, 'sigma_r': SIGMA_R, 'normal_iters': NORMAL_ITERS,
                     'vertex_iters': VERTEX_ITERS, 'max_move_cm': MAX_MOVE, 'crease_deg': CREASE_DEG,
                     'feature_deg': FEATURE_DEG, 'border_fade_cm': BORDER_FADE}}
header = {'key': KEY, 'triangle_count': int(len(tri)), 'vertex_count': int(len(pos)),
          'position_checksum': float(np.abs(pos.astype(np.float64)).sum()),
          'moved': int(len(moved)), 'normal_triangles': int(len(sel))}
with open(HERE / 'Bake' / 'denoise_plan.bin', 'wb') as f:
    f.write((json.dumps(header) + '\n').encode('utf-8'))
    f.write(moved.astype(np.int32).tobytes())
    f.write(P[moved].astype(np.float32).tobytes())
    f.write(sel.astype(np.int32).tobytes())
    f.write(corner.astype(np.float32).tobytes())
(HERE / 'Bake' / 'denoise_report.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
print('A762_DENOISE_PLAN', json.dumps(report), flush=True)
