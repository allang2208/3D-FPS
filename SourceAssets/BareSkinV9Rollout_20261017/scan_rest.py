"""Scan every target snapshot: rest pinholes (faces against welded vertex normals) and UV-triangle match rate."""
import json, collections
import numpy as np
from rollout import *
from transfer import M4Index, weld
from uvmatch import side_of_row

src = M4Source(); ix = M4Index(src)
idx = json.loads((R / 'snap_index.json').read_text()); rows = []
for key, row in sorted(idx.items(), key=lambda kv: kv[1]['path']):
    t = json.loads((R / 'Snapshots' / (key + '.json')).read_text())
    X = np.array(t['positions']); T = np.array(t['triangles']); N = np.array(t['normals']); UV = np.round(np.array(t['uv0']), 5)
    w, n = weld(X); TW = w[T]
    f = np.cross(X[T[:, 1]] - X[T[:, 0]], X[T[:, 2]] - X[T[:, 0]]); sg = np.sign(np.einsum('ij,ij->', f, N.mean(axis=1))) or 1
    vn = np.zeros((n, 3))
    for k in range(3): np.add.at(vn, TW[:, k], f * sg)
    vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)
    inv = np.einsum('ij,ij->i', f * sg, vn[TW].mean(axis=1)) < 0
    side = [side_of_row(t['weights'][tr[0]]) for tr in T]
    hit = sum(1 for i in range(len(T)) if (side[i], tuple(sorted(tuple(UV[i][c]) for c in range(3)))) in ix.tri_key)
    rows.append(dict(path=row['path'], triangles=len(T), uv_match=hit / len(T), pinholes=int(inv.sum()),
                     pinhole_area_cm2=float((np.linalg.norm(f, axis=1)[inv] / 2).sum()), skin_slots=[s['slot'] for s in t['slots'] if s['skin']],
                     skeleton=t['skeleton'], has_morphs=len(t['morphs'])))
    print('%-90s tris %6d uv %.4f pinholes %4d (%.3f cm2)' % (row['path'][-90:], len(T), hit / len(T), inv.sum(), rows[-1]['pinhole_area_cm2']), flush=True)
(R / 'scan_rest.json').write_text(json.dumps(rows, indent=1))
