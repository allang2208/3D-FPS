"""Surface correspondence through the shared V7 atlas UV0 (independent of pose and triangulation).

Every derived mesh kept the master's UV0 (the skin atlas), with the left and right arms sharing the same
islands. A target corner is located in the M4 triangle of the same arm whose old UV0 contains it; where
UV islands overlap (old palm patches) the candidate closest in the coarsely aligned 3D space wins.
Returns per target corner: M4 triangle index and barycentric coordinates.
"""
import numpy as np
from scipy.spatial import cKDTree


def side_of_row(row):
    s = [b[-1] for b, w in row.items() if w > .01 and b[-2] == '_' and b[-1] in 'lr']
    return max(set(s), key=s.count) if s else 'c'


class UVIndex:
    def __init__(self, src):
        self.src = src
        side = np.array([side_of_row(src.W8[t[0]]) for t in src.T])
        self.side = side; self.uv = src.UV8                       # (tris, 3, 2)
        self.cent3 = src.X8[src.T].mean(axis=1)
        self.trees = {}
        for s in 'lrc':
            idx = np.nonzero(side == s)[0]
            if len(idx): self.trees[s] = (idx, cKDTree(self.uv[idx].mean(axis=1)))

    @staticmethod
    def bary(p, tri):
        a, b, c = tri; v0 = b - a; v1 = c - a; v2 = p - a
        den = v0[0] * v1[1] - v1[0] * v0[1]
        if abs(den) < 1e-14: return None
        l1 = (v2[0] * v1[1] - v1[0] * v2[1]) / den; l2 = (v0[0] * v2[1] - v2[0] * v0[1]) / den
        return np.array([1 - l1 - l2, l1, l2])

    def locate(self, uv, side, pos3, k=24):
        """uv: (n,2) corner UVs, side per corner, pos3: (n,3) aligned positions. -> tri (n,), bary (n,3), uv_err (n,)"""
        n = len(uv); tri = -np.ones(n, int); bc = np.zeros((n, 3)); err = np.full(n, 9.0)
        for s in set(side):
            if s not in self.trees: continue
            idx, tree = self.trees[s]; sel = np.nonzero(side == s)[0]
            _, cand = tree.query(uv[sel], k=min(k, len(idx)))
            for r, q in enumerate(sel):
                best = None
                for c in idx[cand[r]]:
                    b = self.bary(uv[q], self.uv[c])
                    if b is None: continue
                    out = -min(b.min(), 0)
                    d3 = np.linalg.norm(self.src.X8[self.src.T[c]].T @ np.clip(b, 0, None) / max(np.clip(b, 0, None).sum(), 1e-9) - pos3[q])
                    score = (out > 1e-3, out if out > 1e-3 else d3)
                    if best is None or score < best[0]: best = (score, c, b, out)
                if best is None: continue
                _, c, b, out = best
                b = np.clip(b, 0, None); b /= b.sum()
                tri[q] = c; bc[q] = b; err[q] = out
        return tri, bc, err
