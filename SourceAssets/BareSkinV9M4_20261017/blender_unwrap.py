"""Blender (background): fresh UV0 for the M4 skin on the V9 rest shape.

Seams = the accepted Manny/V7 UV0 island borders and the existing mesh splits; every island is
re-flattened (angle based), so V7 patch overlaps and the left/right sharing disappear. Texel density is
equalised, the upper arm gets 0.6x, then everything is packed into one 0-1 tile.
Writes Work/uv_new.npy (per snapshot corner, UE V convention) and Work/uv_report.json.
"""
import bpy, bmesh, json, sys
from pathlib import Path
import numpy as np
R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9M4_20261017')

d = np.load(R / 'Work/mesh.npz'); T = d['T']; perm = d['perm']; regions = d['region']
bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new('M4Skin')
me.from_pydata([tuple(p) for p in d['X']], [], [tuple(int(v) for v in t) for t in T]); me.update()
obj = bpy.data.objects.new('M4Skin', me); bpy.context.scene.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj; obj.select_set(True)
old = me.uv_layers.new(name='old'); new = me.uv_layers.new(name='new')
uv = d['UV'].reshape(-1, 2).copy(); uv[:, 1] = 1 - uv[:, 1]
old.data.foreach_set('uv', uv.ravel()); new.data.foreach_set('uv', uv.ravel())
region = me.attributes.new('region', 'INT', 'FACE'); region.data.foreach_set('value', regions.astype(np.int32))
me.uv_layers.active = old
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.select_all(action='SELECT'); bpy.ops.uv.seams_from_islands(mark_seams=True)
me_edit = bmesh.from_edit_mesh(me)
seams = sum(e.seam for e in me_edit.edges); boundary = sum(e.is_boundary for e in me_edit.edges)
bpy.ops.object.mode_set(mode='OBJECT')
me.uv_layers.active = me.uv_layers['new']
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.unwrap(method='ANGLE_BASED', fill_holes=True, correct_aspect=True, margin=0.001)
bpy.ops.uv.select_all(action='SELECT'); bpy.ops.uv.average_islands_scale()
bm = bmesh.from_edit_mesh(me); lay = bm.loops.layers.uv['new']; reg = bm.faces.layers.int['region']
bm.faces.ensure_lookup_table()
# islands by shared UV-connected edges (seams split islands)
parent = list(range(len(bm.faces)))
def find(a):
    while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
    return a
for e in bm.edges:
    if e.seam or len(e.link_faces) != 2: continue
    a, b = e.link_faces; parent[find(a.index)] = find(b.index)
islands = {}
for f in bm.faces: islands.setdefault(find(f.index), []).append(f)
scaled = 0
for faces in islands.values():
    regs = [f[reg] for f in faces]
    if regs.count(0) * 2 < len(regs): continue
    pts = [l[lay].uv.copy() for f in faces for l in f.loops]; c = sum(pts, pts[0] * 0) / len(pts)
    for f in faces:
        for l in f.loops: l[lay].uv = c + (l[lay].uv - c) * 0.6
    scaled += 1
bmesh.update_edit_mesh(me)
bpy.ops.uv.select_all(action='SELECT')
bpy.ops.uv.pack_islands(rotate=True, rotate_method='ANY', scale=True, merge_overlap=False, margin_method='FRACTION', margin=0.004, shape_method='CONCAVE')
bpy.ops.object.mode_set(mode='OBJECT')
out = np.zeros(len(me.loops) * 2); me.uv_layers['new'].data.foreach_get('uv', out); out = out.reshape(-1, 3, 2)
out[:, :, 1] = 1 - out[:, :, 1]
inv = np.argsort(perm); np.save(R / 'Work/uv_new.npy', out[:, inv])      # back to snapshot corner order
area3 = np.array([p.area for p in me.polygons])
e1 = out[:, 1] - out[:, 0]; e2 = out[:, 2] - out[:, 0]
uvarea = np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]) / 2
dens = np.sqrt(uvarea * 4096 ** 2 / np.maximum(area3, 1e-9))
rep = dict(islands=len(islands), upper_arm_islands_scaled=scaled, seams=int(seams), boundary_edges=int(boundary),
           uv_coverage=float(uvarea.sum()),
           texels_per_cm_4096={str(r): dict(median=float(np.median(dens[regions == r])), p10=float(np.percentile(dens[regions == r], 10)),
                                            p90=float(np.percentile(dens[regions == r], 90))) for r in (0, 1, 2)})
(R / 'Work/uv_report.json').write_text(json.dumps(rep, indent=1))
bpy.ops.wm.save_as_mainfile(filepath=str(R / 'Work/M4_SkinV9_UV.blend'))
print('M4V9_UV', json.dumps(rep))
