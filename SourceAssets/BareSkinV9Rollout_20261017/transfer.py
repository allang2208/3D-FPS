"""Transfer the accepted M4 V9 surface onto one target skin snapshot (offline, numpy).

Correspondence: every derived mesh kept the master's UV0 exactly, so a target triangle is the M4 triangle
with the same arm side and the same UV triple; corners pair by UV. Triangles the V8 repair rebuilt
differently fall back to UV location inside nearby M4 triangles. Per target vertex a local rotation
(Kabsch on the matched 2-ring) carries M4's rest-space changes into the target's own bind pose, so
pre-bent references (ASH12 / M16 / pistols) receive the same anatomy in their own frame.

Output dict (all in target order): positions, corner normals, corner UV0, changed weight rows,
triangle region labels (0 upper arm, 1 forearm, 2 hand), refit vertex set, and match statistics.
"""
import collections
import numpy as np
from scipy.spatial import cKDTree
from uvmatch import side_of_row
from rollout import bone_alias


def kabsch_R(A, B):
    H = A.T @ B; U, S, Vt = np.linalg.svd(H); D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
    return Vt.T @ D @ U.T


class M4Index:
    def __init__(self, src):
        self.src = src; T = src.T; UV = np.round(src.UV8, 5)
        self.side = np.array([side_of_row(src.W8[t[0]]) for t in T])
        self.tri_key = {}
        for i, t in enumerate(T):
            self.tri_key[(self.side[i], tuple(sorted(tuple(UV[i][c]) for c in range(3))))] = i
        self.uvr = UV
        self.w = src.weld; self.nw = int(self.w.max()) + 1
        self.P8 = np.zeros((self.nw, 3)); self.P8[self.w] = src.X8
        self.P9 = np.zeros((self.nw, 3)); self.P9[self.w] = src.X9
        self.W8w = {}; self.W9w = {}
        for v in range(len(src.X8)): self.W8w.setdefault(self.w[v], src.W8[v]); self.W9w.setdefault(self.w[v], src.W9[v])
        self.changed_w = {k for k in self.W8w if self.W8w[k] != self.W9w[k]}
        self.cent = src.X8[T].mean(axis=1)
        self.uvcent = {s: (np.nonzero(self.side == s)[0], cKDTree(src.UV8[self.side == s].mean(axis=1))) for s in set(self.side)}
        # seam band weight (old hand/forearm split + upper-arm join), as in BareSkinV9M4 normals.py
        TW = self.w[T]; reg = src.region
        def seam(a, b):
            sa = {v for i, t in enumerate(TW) if reg[i] == a for v in t}
            return sa & {v for i, t in enumerate(TW) if reg[i] == b for v in t}
        ring = sorted(seam(1, 2) | seam(0, 1))
        d = cKDTree(self.P9[ring]).query(self.P9)[0]
        b = 1 - np.clip((d - .6) / 1.6, 0, 1); self.band = b * b * (3 - 2 * b)


def weld(X, digits=4):
    key = {}; w = np.zeros(len(X), int)
    for v, p in enumerate(np.round(X, digits)): w[v] = key.setdefault(tuple(p), len(key))
    return w, len(key)


def bary(p, tri):
    a, b, c = tri; v0 = b - a; v1 = c - a; v2 = p - a
    den = v0[0] * v1[1] - v1[0] * v0[1]
    if abs(den) < 1e-14: return np.array([1 / 3, 1 / 3, 1 / 3])
    l1 = (v2[0] * v1[1] - v1[0] * v2[1]) / den; l2 = (v0[0] * v2[1] - v2[0] * v0[1]) / den
    return np.array([1 - l1 - l2, l1, l2])


def map_weights(row_t, w8, w9, tgt_bones):
    """Apply the M4 V9 weight change (w8 -> w9, M4 bone names) to a target row (target bone names)."""
    out = dict(row_t)
    for b in set(w8) | set(w9):
        d = w9.get(b, 0) - w8.get(b, 0)
        if abs(d) < 1e-6: continue
        tb = b if b in tgt_bones else None
        if tb is None:
            for cand in ('lowerarm_aux_' + b[-1] if b.startswith('lowerarm') else '', b.split('_twist_')[0] + '_' + b[-1] if '_twist_' in b else ''):
                if cand and cand in tgt_bones: tb = cand; break
        if tb is None: continue
        out[tb] = out.get(tb, 0) + d
    out = {b: x for b, x in out.items() if x > 1e-4}
    s = sum(out.values())
    return {b: x / s for b, x in out.items()} if s > 0 else dict(row_t)


def propagate_match(tgt, ix, X, T, tw, tn, tri_map, corner_map):
    """Vertex matches seeded by exact rest positions (raw or canonical rebind), grown across the welded
    graph by edge-vector agreement in a local frame; triangles then pair by welded triples."""
    import heapq
    from rollout import canonical
    src = ix.src
    Xw = np.zeros((tn, 3)); Xw[tw] = X
    Xc, _, _ = canonical(tgt, src); Xcw = np.zeros((tn, 3)); Xcw[tw] = Xc
    tree = cKDTree(ix.P8)
    d0, i0 = tree.query(Xw); d1, i1 = tree.query(Xcw)
    use = (d1 < 1e-3).sum() > (d0 < 1e-3).sum()
    d, wi = (d1, i1) if use else (d0, i0)
    match = -np.ones(tn, int); used = -np.ones(ix.nw, int)
    for v in np.argsort(d):
        if d[v] > 1e-3: break
        if used[wi[v]] < 0: match[v] = wi[v]; used[wi[v]] = v
    TW = tw[T]; nb = [set() for _ in range(tn)]
    for a, b, c in TW: nb[a] |= {b, c}; nb[b] |= {a, c}; nb[c] |= {a, b}
    nb = [np.array(sorted(s)) for s in nb]
    mnb = [set() for _ in range(ix.nw)]
    for a, b, c in ix.w[src.T]: mnb[a] |= {b, c}; mnb[b] |= {a, c}; mnb[c] |= {a, b}
    mnb = [np.array(sorted(s)) for s in mnb]
    heap = []

    def push(v):
        m = match[v]; ring = [u for u in nb[v] if match[u] >= 0]
        Rm = kabsch_R(Xw[ring] - Xw[v], ix.P8[match[ring]] - ix.P8[m]) if len(ring) >= 3 else np.eye(3)
        for u in nb[v]:
            if match[u] >= 0: continue
            dt = Rm @ (Xw[u] - Xw[v]); cand = [c for c in mnb[m] if used[c] < 0]
            if not cand: continue
            err = np.linalg.norm(ix.P8[cand] - ix.P8[m] - dt, axis=1); k = int(np.argmin(err))
            rel = err[k] / max(np.linalg.norm(dt), 1e-6); second = np.partition(err, 1)[1] if len(err) > 1 else 9e9
            if rel < .5 and second > 1.2 * err[k]: heapq.heappush(heap, (rel, int(u), int(cand[k])))
    for v in np.nonzero(match >= 0)[0]: push(v)
    while heap:
        _, u, c = heapq.heappop(heap)
        if match[u] >= 0 or used[c] >= 0: continue
        match[u] = c; used[c] = u; push(u)
    M4tri = {tuple(sorted(t)): j for j, t in enumerate(ix.w[src.T])}
    tri_map = tri_map.copy(); corner_map = corner_map.copy()
    for i, t in enumerate(TW):
        if tri_map[i] >= 0 or (match[t] < 0).any(): continue
        j = M4tri.get(tuple(sorted(match[t])), -1)
        if j < 0: continue
        wj = list(ix.w[src.T[j]]); corner_map[i] = [wj.index(match[v]) for v in t]; tri_map[i] = j
    return tri_map, corner_map


def transfer(tgt, ix):
    src = ix.src
    X = np.array(tgt['positions']); T = np.array(tgt['triangles']); UV = np.round(np.array(tgt['uv0']), 5)
    N = np.array(tgt['normals']); W = tgt['weights']; nt = len(T)
    side = np.array([side_of_row(W[t[0]]) for t in T])
    tri_map = -np.ones(nt, int); corner_map = -np.ones((nt, 3), int)
    for i, t in enumerate(T):
        j = ix.tri_key.get((side[i], tuple(sorted(tuple(UV[i][c]) for c in range(3)))), -1)
        if j < 0: continue
        for c in range(3):
            for c2 in range(3):
                if tuple(ix.uvr[j][c2]) == tuple(UV[i][c]): corner_map[i, c] = c2
        if (corner_map[i] >= 0).all() and len(set(corner_map[i])) == 3: tri_map[i] = j
        else: corner_map[i] = -1
    if (tri_map >= 0).mean() < .5:
        # UV0 lost on this mesh (RSH12 family): match by rest position (same bind as M4 or its canonical rebind)
        from rollout import canonical
        Xc, _, _ = canonical(tgt, src)
        for Y in (X, Xc):
            d, wi = cKDTree(ix.P8).query(Y)
            if np.median(d) < 1e-3: break
        if np.median(d) < 1e-3:
            M4tri = {tuple(sorted(ix.w[src.T[j]])): j for j in range(len(src.T))}
            for i, t in enumerate(T):
                if d[t].max() > 2e-3: continue
                key = tuple(sorted(wi[t]))
                j = M4tri.get(key, -1)
                if j < 0: continue
                wj = list(ix.w[src.T[j]])
                corner_map[i] = [wj.index(wi[v]) for v in t]; tri_map[i] = j
    uv_coverage = float((tri_map >= 0).mean())
    tw, tn = weld(X); adj = collections.defaultdict(set)
    for a, b, c in T: adj[a] |= {b, c}; adj[b] |= {a, c}; adj[c] |= {a, b}
    if (tri_map >= 0).mean() < .9:
        # partly re-modelled meshes (axe / pickaxe): exact-position seeds grown across the welded graph
        tri_map, corner_map = propagate_match(tgt, ix, X, T, tw, tn, tri_map, corner_map)
    # vertex correspondence (welded M4 vertex) from matched corners
    vmatch = -np.ones(len(X), int); conflicts = 0
    for i in np.nonzero(tri_map >= 0)[0]:
        for c in range(3):
            v = T[i, c]; w = ix.w[src.T[tri_map[i], corner_map[i, c]]]
            if vmatch[v] < 0: vmatch[v] = w
            elif vmatch[v] != w: conflicts += 1
    # local rotation per target vertex (target bind -> M4 rest), from the matched 2-ring
    Rv = np.tile(np.eye(3), (len(X), 1, 1)); have = vmatch >= 0
    for v in range(len(X)):
        ring = adj[v] | {v}
        ring = ring | {u for r in list(ring) for u in adj[r]}
        ring = [u for u in ring if vmatch[u] >= 0]
        if len(ring) >= 4:
            A = X[ring] - X[ring].mean(axis=0); B = ix.P8[vmatch[ring]] - ix.P8[vmatch[ring]].mean(axis=0)
            Rv[v] = kabsch_R(A, B)               # maps target vectors into M4 rest
    geometric = uv_coverage < .9
    if geometric:
        # unmatched vertices: carried into M4 rest from their nearest matched vertex, then onto the M4 surface
        mv = np.nonzero(have)[0]; mtree = cKDTree(X[mv])
        _, near = mtree.query(X); a = mv[near]
        pm = ix.P8[np.maximum(vmatch[a], 0)] + np.einsum('vij,vj->vi', Rv[a], X - X[a])
        pm[have] = ix.P8[vmatch[have]]
        ctree = cKDTree(ix.cent)
    fallback = []
    for i in np.nonzero(tri_map < 0)[0]:
        if geometric:
            cen = pm[T[i]].mean(axis=0); _, cand = ctree.query(cen, k=8)
            j = min(np.atleast_1d(cand), key=lambda j: np.linalg.norm(ix.cent[j] - cen)); fallback.append((i, int(j))); continue
        # unmatched triangles: locate their UV centroid in an M4 triangle near their matched neighbours
        idx, tree = ix.uvcent[side[i]]
        nearm = [vmatch[u] for v in T[i] for u in adj[v] | {v} if vmatch[u] >= 0]
        _, cand = tree.query(UV[i].mean(axis=0), k=min(32, len(idx)))
        best = None
        for j in idx[np.atleast_1d(cand)]:
            b = bary(UV[i].mean(axis=0), src.UV8[j]); out = -min(b.min(), 0)
            d3 = min((np.linalg.norm(ix.cent[j] - ix.P8[nearm], axis=1).min() if nearm else 0), 99)
            score = (out > 1e-3, d3 if out <= 1e-3 else out)
            if best is None or score < best[0]: best = (score, j)
        fallback.append((i, best[1]))

    def corner_bary(i, c, j):
        if not geometric: return bary(UV[i][c], src.UV8[j])
        A3 = src.X8[src.T[j]]; e1, e2 = A3[1] - A3[0], A3[2] - A3[0]; q = pm[T[i, c]] - A3[0]
        G = np.array([[e1 @ e1, e1 @ e2], [e1 @ e2, e2 @ e2]]); r = np.array([q @ e1, q @ e2])
        try: l1, l2 = np.linalg.solve(G, r)
        except np.linalg.LinAlgError: l1 = l2 = 1 / 3
        return np.clip(np.array([1 - l1 - l2, l1, l2]), -.5, 1.5)
    # rest positions: M4 rest delta rotated into the target frame
    delta = np.zeros_like(X)
    delta[have] = np.einsum('vji,vj->vi', Rv[have], ix.P9[vmatch[have]] - ix.P8[vmatch[have]])
    for i, j in fallback:                         # interpolate the delta for unmatched corners
        for c in range(3):
            v = T[i, c]
            if have[v]: continue
            b = np.clip(corner_bary(i, c, j), 0, None); b /= max(b.sum(), 1e-9)
            dm = (ix.P9[ix.w[src.T[j]]] - ix.P8[ix.w[src.T[j]]]).T @ b
            delta[v] = Rv[v].T @ dm
    newX = X + delta
    # geometric fold-overs of this target (winding consistent, sheet folded back): local untangle
    TW = tw[T]
    def face_dirs(Xw_):
        f = np.cross(Xw_[TW[:, 1]] - Xw_[TW[:, 0]], Xw_[TW[:, 2]] - Xw_[TW[:, 0]])
        return f * sgn
    Xw = np.zeros((tn, 3)); Xw[tw] = newX
    f0 = np.cross(X[T[:, 1]] - X[T[:, 0]], X[T[:, 2]] - X[T[:, 0]])
    sgn = np.sign(np.einsum('ij,ij->', f0, N.mean(axis=1))) or 1.0       # outward sign of (b-a)x(c-a)
    nbw = [set() for _ in range(tn)]
    for a, b, c in TW: nbw[a] |= {b, c}; nbw[b] |= {a, c}; nbw[c] |= {a, b}
    nbw = [np.array(sorted(s)) for s in nbw]
    def vnormals(Xw_):
        f = face_dirs(Xw_); vn = np.zeros((tn, 3))
        for k in range(3): np.add.at(vn, TW[:, k], f)
        return vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)
    def inverted(Xw_):
        return np.nonzero(np.einsum('ij,ij->i', face_dirs(Xw_), vnormals(Xw_)[TW].mean(axis=1)) < 0)[0]
    bad = inverted(Xw); untangle = set(); pinholes_before = int(len(bad))
    # remaining folds of this target: bounded local relaxation (<= 2 mm), kept only where it helps; the
    # held-pose grip correctives untangle what is left in the poses that are actually shown
    if len(bad):
        zone = {int(v) for t in TW[bad] for v in t}
        for _ in range(2): zone |= {int(u) for v in list(zone) for u in nbw[v]}
        zone = np.array(sorted(zone)); start = Xw.copy(); best = (len(bad), Xw.copy())
        for _ in range(80):
            avg = np.array([Xw[nbw[v]].mean(axis=0) for v in zone]); Xw[zone] += .5 * (avg - Xw[zone])
            step = Xw - start; mag = np.linalg.norm(step, axis=1); Xw = start + step * np.minimum(1, .2 / np.maximum(mag, 1e-9))[:, None]
            nb_bad = len(inverted(Xw))
            if nb_bad < best[0]: best = (nb_bad, Xw.copy())
            if not nb_bad: break
        Xw = best[1]
        moved = np.nonzero(np.linalg.norm(Xw - start, axis=1) > 1e-5)[0]; untangle = set(moved.tolist())
    # sliver folds that stay (HK416 / G18 / Pit Viper family: creased slivers all over their own surface):
    # tangential relaxation - vertices slide inside the smoothed surface (<= 4 mm along it, <= 0.3 mm off
    # it), which flips in-plane folds back without changing the arm's shape; kept only where it helps
    rebuilt = 0.0
    bad = inverted(Xw)
    if len(bad):
        S_ = Xw.copy()
        for _ in range(6): S_ = .5 * S_ + .5 * np.array([S_[nbw[v]].mean(axis=0) if len(nbw[v]) else S_[v] for v in range(tn)])
        nrm = vnormals(S_)
        start = Xw.copy(); best = (len(bad), Xw.copy())
        for rings in (2, 4):
            zone = {int(v) for t in TW[bad] for v in t}
            for _ in range(rings): zone |= {int(u) for v in list(zone) for u in nbw[v]}
            zone = np.array(sorted(zone))
            for _ in range(150):
                avg = np.array([Xw[nbw[v]].mean(axis=0) for v in zone]); step = avg - Xw[zone]
                step -= np.einsum('ij,ij->i', step, nrm[zone])[:, None] * nrm[zone]
                Xw[zone] += .5 * step
                d = Xw - start; dn = np.einsum('ij,ij->i', d, nrm)[:, None] * nrm; dt = d - dn
                tm = np.linalg.norm(dt, axis=1); nm = np.linalg.norm(dn, axis=1)
                Xw = start + dt * np.minimum(1, .4 / np.maximum(tm, 1e-9))[:, None] + dn * np.minimum(1, .03 / np.maximum(nm, 1e-9))[:, None]
                nb_bad = inverted(Xw)
                if len(nb_bad) < best[0]: best = (len(nb_bad), Xw.copy())
                if not len(nb_bad): break
            Xw = best[1].copy(); bad = inverted(Xw)
            if not len(bad): break
        moved = np.linalg.norm(Xw - start, axis=1)
        rebuilt = float(moved.max()); untangle |= {int(v) for v in np.nonzero(moved > 1e-5)[0]}
    pinholes_after = int(len(inverted(Xw)))
    newX = Xw[tw]
    # normals: the target's own normals carried by its geometric change; geometric in seam bands,
    # untangled folds, M4 refit zones and wherever the original normal was already wrong
    Xw0 = np.zeros((tn, 3)); Xw0[tw] = X
    G0 = vnormals(Xw0); G1 = vnormals(Xw)
    bandw = np.zeros(tn)
    for v in range(len(X)):
        if have[v]: bandw[tw[v]] = max(bandw[tw[v]], ix.band[vmatch[v]])
    refit_w = {tw[v] for v in range(len(X)) if have[v] and vmatch[v] in src.refit} | untangle

    def rotate(v, a, b):
        ax = np.cross(a, b); s = np.linalg.norm(ax); c = a @ b
        if s < 1e-9: return v
        ax /= s; th = np.arctan2(s, c)
        return v * np.cos(th) + np.cross(ax, v) * np.sin(th) + ax * (ax @ v) * (1 - np.cos(th))

    uv9 = np.zeros((nt, 3, 2)); n9 = np.zeros((nt, 3, 3)); region = np.zeros(nt, int)
    for i in range(nt):
        for c in range(3):
            w_ = tw[T[i, c]]; n0 = N[i, c] / max(np.linalg.norm(N[i, c]), 1e-9)
            if w_ in refit_w or n0 @ G0[w_] < .2: n = G1[w_]
            else:
                n = rotate(n0, G0[w_], G1[w_]); bw = bandw[w_]
                n = (1 - bw) * n + bw * G1[w_]
            n9[i, c] = n / max(np.linalg.norm(n), 1e-9)
    for i in np.nonzero(tri_map >= 0)[0]:
        j = tri_map[i]; region[i] = src.region[j]
        for c in range(3): uv9[i, c] = src.UV9[j, corner_map[i, c]]
    for i, j in fallback:
        region[i] = src.region[j]
        for c in range(3): uv9[i, c] = corner_bary(i, c, j) @ src.UV9[j]
    # weights
    tgt_bones = set(tgt['bones'])
    new_w = {}
    for v in np.nonzero(have)[0]:
        w = vmatch[v]
        if w in ix.changed_w:
            row = map_weights(W[v], ix.W8w[w], ix.W9w[w], tgt_bones)
            if row != W[v]: new_w[int(v)] = row
    stats = dict(triangles=int(nt), matched=int((tri_map >= 0).sum()), fallback=len(fallback), vertex_conflicts=int(conflicts),
                 vertices=int(len(X)), vertices_matched=int(have.sum()), weights_changed=len(new_w),
                 max_delta_cm=float(np.linalg.norm(newX - X, axis=1).max()), pinholes_before=pinholes_before, pinholes_after=pinholes_after,
                 untangled_vertices=len(untangle), rebuilt_max_cm=rebuilt)
    refit = {int(v) for v in range(len(X)) if tw[v] in refit_w}
    return dict(positions=newX, normals=n9, uv0=uv9, weights=new_w, region=region, refit=refit, stats=stats,
                tri_map=tri_map, vmatch=vmatch, Rv=Rv, side=side)


