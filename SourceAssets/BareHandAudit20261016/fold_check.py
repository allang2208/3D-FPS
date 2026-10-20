"""Classify faces whose stored normal opposes their winding: true geometric folds vs. shading-only."""
import json, sys
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np
from audit_mesh import side_and_region


def classify(d):
    v = np.asarray(d['positions']); t = np.asarray(d['triangles']); n = np.asarray(d['normals']); W = d['weights']
    key = np.round(v / 1e-4).astype(np.int64)
    _, wid = np.unique(key, axis=0, return_inverse=True); wid = wid.ravel(); tw = wid[t]
    cr = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]])
    area = .5 * np.linalg.norm(cr, axis=1)
    gn = cr / np.maximum(np.linalg.norm(cr, axis=1, keepdims=True), 1e-12)
    sn = n.mean(1); sn /= np.maximum(np.linalg.norm(sn, axis=1, keepdims=True), 1e-12)
    dots = np.einsum('ij,ij->i', gn, sn); conv = np.sign(np.median(dots))
    odd = set(np.where(dots * conv < 0)[0].tolist())
    edges = defaultdict(list)
    for ti, f in enumerate(tw.tolist()):
        for a, b in zip(f, f[1:] + f[:1]):
            edges[(min(a, b), max(a, b))].append(ti)
    rows = []
    for ti in sorted(odd):
        f = tw[ti].tolist(); nb = set()
        for a, b in zip(f, f[1:] + f[:1]):
            nb.update(x for x in edges[(min(a, b), max(a, b))] if x != ti)
        # A true fold: the face's geometric normal turns > 120 deg from most neighbours.
        dihedral = [float(np.degrees(np.arccos(np.clip(gn[ti] @ gn[x], -1, 1)))) for x in nb]
        ws = Counter()
        for vi in t[ti]: ws.update(W[vi])
        rows.append(dict(face=int(ti), where='/'.join(side_and_region(dict(ws))), area_mm2=round(float(area[ti]) * 100, 4),
                         max_dihedral=round(max(dihedral), 1) if dihedral else None,
                         fold=bool(dihedral) and sum(x > 120 for x in dihedral) >= 2))
    return rows


if __name__ == '__main__':
    d = json.loads(Path(sys.argv[1]).read_text())
    rows = classify(d)
    folds = [r for r in rows if r['fold']]
    print(len(rows), 'opposed faces;', len(folds), 'geometric folds;', 'total area mm2 %.3f' % sum(r['area_mm2'] for r in rows))
    print('folds by region', Counter(r['where'] for r in folds).most_common(12))
    print('shading-only by region', Counter(r['where'] for r in rows if not r['fold']).most_common(12))
    print('largest', sorted(rows, key=lambda r: -r['area_mm2'])[:8])
