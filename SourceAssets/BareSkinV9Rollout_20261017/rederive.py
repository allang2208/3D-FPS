"""Re-derive a distorted FBX-family hand mesh from a clean V9 sibling with the identical arm skeleton.

HK416 / SteelWarhammer share the M4 arm skeleton exactly, G18 / Pit Viper (single and dual) the M1911 ones.
Their own skin was exported twisted and crumpled, so nothing of its shape is kept: every vertex takes the
V9 position, weights and normal of its master counterpart on the clean sibling (correspondence through the
shared master UV0), and the few vertices without a counterpart are filled harmonically from their
neighbours. Triangles, vertex IDs, UV0 (new V9 layout) and material slots stay those of the target.
"""
import collections
import numpy as np
from rollout import load_snapshot, M4_PATH
from transfer import transfer, weld


def template_table(template, ix):
    """Clean V9 data per M4 welded vertex: position, weight row, vertex normal."""
    src = ix.src
    if template == M4_PATH:
        pos = ix.P9.copy(); wts = [ix.W9w[w] for w in range(ix.nw)]
        nrm = np.zeros((ix.nw, 3))
        for j, tri in enumerate(src.T):
            for c in range(3): nrm[ix.w[tri[c]]] += src.N9[j, c]
        nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
        return pos, wts, nrm, np.ones(ix.nw, bool)
    s = load_snapshot(template); r = transfer(s, ix)
    pos = np.zeros((ix.nw, 3)); nrm = np.zeros((ix.nw, 3)); wts = [None] * ix.nw; have = np.zeros(ix.nw, bool)
    rows = [dict(x) for x in s['weights']]
    for v, row in r['weights'].items(): rows[int(v)] = row
    T = np.array(s['triangles']); vn = np.zeros((len(r['positions']), 3))
    for i, tri in enumerate(T):
        for c in range(3): vn[tri[c]] += r['normals'][i, c]
    vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)
    for v, m in enumerate(r['vmatch']):
        if m >= 0 and not have[m]: pos[m] = r['positions'][v]; nrm[m] = vn[v]; wts[m] = rows[v]; have[m] = True
    return pos, wts, nrm, have


def rederive(tgt, template, ix):
    r = transfer(tgt, ix)                                  # correspondence, new UV0, regions
    pos, wts, nrm, have_t = template_table(template, ix)
    X0 = np.array(tgt['positions']); T = np.array(tgt['triangles']); n = len(X0)
    bones = set(tgt['bones'])
    vm = r['vmatch']; known = np.array([vm[v] >= 0 and have_t[vm[v]] for v in range(n)])
    X = X0.copy(); W = [dict(x) for x in tgt['weights']]; VN = np.zeros((n, 3))
    for v in np.nonzero(known)[0]:
        X[v] = pos[vm[v]]; VN[v] = nrm[vm[v]]
        row = {b: x for b, x in wts[vm[v]].items() if b in bones}; s_ = sum(row.values()); W[v] = {b: x / s_ for b, x in row.items()}
    # harmonic fill of vertices without a clean counterpart (welded graph, known vertices fixed)
    tw, tn = weld(X0); nb = [set() for _ in range(tn)]
    for a, b, c in tw[T]: nb[a] |= {b, c}; nb[b] |= {a, c}; nb[c] |= {a, b}
    kw = np.zeros(tn, bool); Pw = np.zeros((tn, 3)); Ww = [None] * tn
    for v in range(n):
        if known[v]: kw[tw[v]] = True; Pw[tw[v]] = X[v]; Ww[tw[v]] = W[v]
    unk = [w for w in range(tn) if not kw[w]]
    for w in unk:
        k = [u for u in nb[w] if kw[u]]
        Pw[w] = Pw[k].mean(axis=0) if k else Pw[w]
    for _ in range(200):
        for w in unk: Pw[w] = Pw[list(nb[w])].mean(axis=0)
    for _ in range(3):
        for w in unk:
            rows = [Ww[u] for u in nb[w] if Ww[u]]
            if not rows: continue
            acc = collections.Counter()
            for row in rows:
                for b, x in row.items(): acc[b] += x
            s_ = sum(acc.values()); Ww[w] = {b: x / s_ for b, x in acc.items()}
    for v in range(n):
        if not known[v]: X[v] = Pw[tw[v]]; W[v] = Ww[tw[v]] or W[v]
    # vertex normals: clean template normals; geometric where filled
    f = np.cross(X[T[:, 1]] - X[T[:, 0]], X[T[:, 2]] - X[T[:, 0]])
    sg = np.sign(np.einsum('ij,ij->', f, VN[T].mean(axis=1))) or 1.0
    G = np.zeros((tn, 3))
    for k in range(3): np.add.at(G, tw[T][:, k], f * sg)
    G /= np.maximum(np.linalg.norm(G, axis=1, keepdims=True), 1e-12)
    for v in range(n):
        if not known[v]: VN[v] = G[tw[v]]
    inv = int((np.einsum('ij,ij->i', f * sg, G[tw[T]].mean(axis=1)) < 0).sum())
    normals = np.repeat(VN[T][:, :, :], 1, axis=0)
    stats = dict(r['stats']); stats.update(rederived_from=template, filled_vertices=int((~known).sum()),
                                            pinholes_after=inv, max_move_cm=float(np.linalg.norm(X - X0, axis=1).max()))
    return dict(positions=X, normals=normals, uv0=r['uv0'], weights={v: W[v] for v in range(n)}, region=r['region'], stats=stats,
                vmatch=vm, tri_map=r['tri_map'])
