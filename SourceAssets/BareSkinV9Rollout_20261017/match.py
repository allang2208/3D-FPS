"""Topology-propagated correspondence: target welded vertices -> M4 welded vertices.

All targets descend from the same V7 master, so their welded connectivity is (almost) the M4 graph,
while their rest shapes may be bent, re-derived or locally edited. Seeds are mutual nearest neighbours
after a coarse alignment; the match then grows across edges, choosing for each neighbour the M4
neighbour whose edge vector agrees best (edge vectors are insensitive to the cm-level drift that defeats
plain nearest-neighbour matching). Triangles are then matched by their welded vertex triples.
"""
import heapq
import numpy as np
from scipy.spatial import cKDTree
from rollout import canonical, bone_alias


def weld(X, digits=4):
    key = {}; w = np.zeros(len(X), int)
    for v, p in enumerate(np.round(X, digits)): w[v] = key.setdefault(tuple(p), len(key))
    return w, len(key)


def adjacency(TW, n):
    nb = [set() for _ in range(n)]
    for a, b, c in TW:
        nb[a] |= {b, c}; nb[b] |= {a, c}; nb[c] |= {a, b}
    return [np.array(sorted(s)) for s in nb]


def kabsch(A, B):
    ca = A.mean(0); cb = B.mean(0); H = (A - ca).T @ (B - cb); U, S, Vt = np.linalg.svd(H)
    D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))]); Rm = Vt.T @ D @ U.T
    M = np.eye(4); M[:3, :3] = Rm; M[:3, 3] = cb - Rm @ ca; return M


class M4Graph:
    def __init__(self, src):
        self.src = src
        self.w, self.n = src.weld, int(src.weld.max()) + 1
        self.P = np.zeros((self.n, 3)); self.P[self.w] = src.X8
        self.TW = self.w[src.T]; self.nb = adjacency(self.TW, self.n)
        self.tree = cKDTree(self.P)
        self.tri_of = {tuple(sorted(t)): i for i, t in enumerate(self.TW)}
        dom = {}
        for v in range(len(src.X8)): dom[self.w[v]] = max(src.W8[v], key=src.W8[v].get)
        self.dom = np.array([dom[i] for i in range(self.n)])


def align(tgt, g):
    """Coarse alignment: canonical rebind or raw, whichever is closer, then per-bone rigid ICP."""
    X = np.array(tgt['positions']); Xc, _, _ = canonical(tgt, g.src)
    d0, _ = g.tree.query(X); d1, _ = g.tree.query(Xc)
    Y0 = X if np.median(d0) <= np.median(d1) else Xc
    dom = np.array([bone_alias(max(w, key=w.get), g.src.B) or '' for w in tgt['weights']])
    T = {}
    for b in set(dom):
        sel = np.nonzero(dom == b)[0]; ms = np.nonzero(g.dom == b)[0]
        if len(sel) < 6 or len(ms) < 6: continue
        tree = cKDTree(g.P[ms]); Y = Y0[sel]; M = np.eye(4)
        for _ in range(15):
            d, i = tree.query(Y); keep = d < max(3 * np.median(d), .05)
            if keep.sum() < 4: break
            M = kabsch(Y0[sel][keep], g.P[ms][i[keep]]); Y = (M[:3, :3] @ Y0[sel].T).T + M[:3, 3]
        T[b] = M
    Y = np.zeros_like(X)
    for v, row in enumerate(tgt['weights']):
        acc = np.zeros((4, 4)); tot = 0
        for bn, wt in row.items():
            a = bone_alias(bn, g.src.B)
            if a in T: acc += wt * T[a]; tot += wt
        Y[v] = (acc[:3, :3] @ Y0[v] + acc[:3, 3]) / 1 if tot > 0 else Y0[v]
        if tot > 0: Y[v] = (acc / tot)[:3, :3] @ Y0[v] + (acc / tot)[:3, 3]
    return Y


def correspond(tgt, g):
    X = np.array(tgt['positions']); T = np.array(tgt['triangles'])
    if T.shape == g.src.T.shape and (T == g.src.T).all() and np.abs(np.array(tgt['positions']).shape[0] - len(g.src.X8)) == 0:
        same = True
    else:
        same = False
    tw, tn = weld(X); TW = tw[T]; tnb = adjacency(TW, tn)
    Xw = np.zeros((tn, 3)); Xw[tw] = X
    Y = align(tgt, g); Yw = np.zeros((tn, 3)); Yw[tw] = Y
    match = -np.ones(tn, int); used = -np.ones(g.n, int)
    rot = [None] * tn

    def ring_fit(v, m):
        """Local rotation target->M4 and residual from the 1-ring (greedy edge-vector assignment)."""
        a = Xw[tnb[v]] - Xw[v]; b = g.P[g.nb[m]] - g.P[m]
        if len(a) != len(b) or len(a) < 3: return None, 9e9
        Rm = np.eye(3)
        for _ in range(3):
            ar = a @ Rm.T; cost = np.linalg.norm(ar[:, None] - b[None], axis=2)
            j = cost.argmin(axis=1)
            if len(set(j.tolist())) < len(j): return None, 9e9
            M = kabsch(a, b[j]); Rm = M[:3, :3]
        res = np.linalg.norm(a @ Rm.T - b[j], axis=1).mean() / max(np.linalg.norm(b, axis=1).mean(), 1e-6)
        return Rm, res

    # seeds: close mutual nearest neighbours whose 1-ring shape agrees (insensitive to global drift)
    d, i = g.tree.query(Yw); back = cKDTree(Yw).query(g.P)[1]
    seeds = []
    for v in np.argsort(d):
        if d[v] > 1.5 or len(seeds) > 4000: break
        if back[i[v]] != v or used[i[v]] >= 0: continue
        Rm, res = ring_fit(v, i[v])
        if Rm is not None and res < .08: match[v] = i[v]; used[i[v]] = v; rot[v] = Rm; seeds.append(v)
    heap = []

    def push(v):
        m = match[v]
        nbrs = [u for u in tnb[v] if match[u] >= 0]
        if len(nbrs) >= 3:
            M = kabsch(Xw[nbrs] - Xw[v], g.P[match[nbrs]] - g.P[m]); rot[v] = M[:3, :3]
        Rm = rot[v] if rot[v] is not None else np.eye(3)
        for nv in tnb[v]:
            if match[nv] >= 0: continue
            dt = Rm @ (Xw[nv] - Xw[v]); cand = [c for c in g.nb[m] if used[c] < 0]
            if not cand: continue
            err = np.linalg.norm(g.P[cand] - g.P[m] - dt, axis=1); k = int(np.argmin(err))
            rel = err[k] / max(np.linalg.norm(dt), 1e-6)
            second = np.partition(err, 1)[1] if len(err) > 1 else 9e9
            if rel < .5 and second > 1.2 * err[k]:
                rot[nv] = Rm; heapq.heappush(heap, (rel, int(nv), int(cand[k])))
    for v in np.nonzero(match >= 0)[0]: push(v)
    while heap:
        rel, nv, c = heapq.heappop(heap)
        if match[nv] >= 0 or used[c] >= 0: continue
        match[nv] = c; used[c] = nv; push(nv)
    # triangle correspondence by welded triples
    tri_map = -np.ones(len(T), int)
    for ti, t in enumerate(TW):
        if (match[t] >= 0).all(): tri_map[ti] = g.tri_of.get(tuple(sorted(match[t])), -1)
    if same: tri_map = np.arange(len(T)); match_full = True
    return dict(weld=tw, n=tn, match=match, tri_map=tri_map, aligned=Y, same_topology=same,
                vertex_coverage=float((match >= 0).mean()), triangle_coverage=float((tri_map >= 0).mean()), seeds=len(seeds))
