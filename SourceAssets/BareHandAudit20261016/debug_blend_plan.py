"""Blender: run plan_mesh on one object and explain the normal replacements (read-only)."""
import bpy, sys
import numpy as np
from pathlib import Path
R = Path(__file__).resolve().parent; sys.path.insert(0, str(R))
from generic_fix import plan_mesh, welded, convention
path, objname = sys.argv[sys.argv.index('--') + 1:][:2]
bpy.ops.wm.open_mainfile(filepath=path)
obj = bpy.data.objects[objname]; mesh = obj.data
polys = list(mesh.polygons); cn = [tuple(n.vector) for n in mesh.corner_normals]
d = dict(positions=[list(v.co * 100) for v in mesh.vertices], triangles=[list(p.vertices) for p in polys],
         normals=[[cn[li] for li in p.loop_indices] for p in polys], uv=[[(0, 0)] * 3 for _ in polys],
         triangle_materials=[p.material_index for p in polys], weights=[{} for _ in mesh.vertices])
v, wid = welded(d); t = np.asarray(d['triangles']); n = np.asarray(d['normals'])
print('verts', len(v), 'welded', wid.max() + 1, 'tris', len(t), 'conv', convention(v, t, n), 'bbox cm', np.ptp(v, axis=0).round(2))
from collections import Counter
fw = Counter(tuple(sorted(wid[f])) for f in t.tolist()); print('duplicate welded faces', sum(c - 1 for c in fw.values() if c > 1))
pn = np.array([p.normal[:] for p in polys])
print('face0 p.normal', np.round(pn[0], 3), 'verts', list(polys[0].vertices), 'co', [tuple(round(c, 4) for c in mesh.vertices[i].co) for i in polys[0].vertices])
cr = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]]); fnn = cr / np.maximum(np.linalg.norm(cr, axis=1, keepdims=True), 1e-12)
sn = n / np.linalg.norm(n, axis=2, keepdims=True)
dots = np.einsum('ij,ikj->ik', fnn, sn)
print('stored vs face: frac corners dot<cos35 %.3f, dot<0 %.3f' % ((dots < np.cos(np.radians(35))).mean(), (dots < 0).mean()))
print('cross vs p.normal agree frac', (np.einsum('ij,ij->i', fnn, pn) > .99).mean(), 'face0 cross', np.round(fnn[0], 3))
ops = plan_mesh(d)
print('notes', dict(ops['notes']))
bad = list(ops['normals'].items())[:5]
for (ti, k), nn in bad:
    f = t[ti]; p = v[f]; fn = np.cross(p[1] - p[0], p[2] - p[0]); fn /= np.linalg.norm(fn)
    print('face', ti, 'stored', np.round(n[ti][k], 3), 'smooth', np.round(nn, 3), 'facen', np.round(fn, 3))
