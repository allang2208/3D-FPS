"""Read-only: report open borders and degenerate geometry in the authored mesh.

    & blender.exe --background SourceAssets/BlastFurnace20260923/Authored/BlastFurnace.blend \
        --python SourceAssets/BlastFurnace20260923/diagnose_topology.py
"""
import bmesh
import bpy
import math
from collections import Counter

obj = bpy.data.objects.get('SM_BlastFurnace')
if obj is None:
    raise SystemExit('SM_BlastFurnace not found in the blend')

mesh = obj.data
bm = bmesh.new()
bm.from_mesh(mesh)
bm.verts.ensure_lookup_table()
bm.faces.ensure_lookup_table()

open_edges = [e for e in bm.edges if len(e.link_faces) == 1]
print('OPEN_EDGE_COUNT', len(open_edges))

degenerate = [(f.index, f.calc_area(), f) for f in bm.faces if f.calc_area() < 1e-9]
print('DEGENERATE_FACE_COUNT', len(degenerate))
for index, area, face in degenerate[:12]:
    co = [v.co for v in face.verts]
    neighbours = {f.material_index for e in face.edges for f in e.link_faces}
    print('DEGEN %2d area=%.3e verts=%d centre=(%.1f,%.1f,%.1f) mats=%s'
          % (index, area, len(co),
             sum(c.x for c in co) / len(co) * 100,
             sum(c.y for c in co) / len(co) * 100,
             sum(c.z for c in co) / len(co) * 100,
             sorted(mesh.materials[i].name for i in neighbours)))

worst = []
for vert in bm.verts:
    normals = []
    for face in vert.link_faces:
        normals.append(face.normal.copy())
    if len(normals) < 2:
        continue
    angle = 0.0
    for i in range(len(normals)):
        for j in range(i + 1, len(normals)):
            dot = max(-1.0, min(1.0, normals[i].dot(normals[j])))
            angle = max(angle, math.degrees(math.acos(dot)))
    worst.append((angle, vert.index, vert.co.copy(), len(vert.link_faces),
                  [mesh.materials[f.material_index].name for f in vert.link_faces]))
worst.sort(key=lambda r: -r[0])
print('WORST_FACE_NORMAL_SPREADS')
for angle, index, co, links, mats in worst[:10]:
    print('  %.1f deg vert=%d at=(%.1f,%.1f,%.1f) linked_faces=%d mats=%s'
          % (angle, index, co.x * 100, co.y * 100, co.z * 100, links, sorted(set(mats))))
bm.free()
