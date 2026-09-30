"""Blender (background): re-bake T_A762_WS_Mask in the seated pose, keeping the UV1 layout.

blender -b --factory-startup -P rebake_seated.py

The first bake (bake_a762.py, 2026-09-30) computed cavity/AO on bind-pose geometry, where
the magazine, bolt and trigger sit away from their runtime places (bolt inside the lower
receiver, magazine in the old magwell), so those parts got occlusion they do not have in
game. This re-bake opens A762_SurfaceBake.blend (same UV1 as the installed mesh), moves the
bake copy into the idle pose, applies the magwell repair (lifted teeth, deleted debris) and
bakes the same mask channels again. The rebuilt catch parts point at the neutral texel
block, which is forced to edge 0 / cavity 0 / AO 1.
"""
import json
import sys
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils.kdtree import KDTree

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import bake_a762 as B  # noqa: E402
import seated  # noqa: E402

bpy.ops.wm.open_mainfile(filepath=str(HERE / 'A762_SurfaceBake.blend'))
scene = B.setup_cycles()
ob = bpy.data.objects['A762_BAKE']
seat, source = B.seat_bake_copy(ob)
plan = json.loads((HERE / 'Bake' / 'magwell_repair.json').read_text(encoding='utf-8'))
_, pos, st, tri, _, _, _ = seated.load('A762_AfterSurface')
flip = np.array([1.0, -1.0, 1.0])

me = ob.data
bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()
moves = {int(k): v for k, v in plan['move_vertices'].items()}
lifted = 0
for i, v in enumerate(bm.verts):
    target = moves.get(int(source[i]))
    if target is not None:  # receiver vertices: bind == seated
        v.co = (np.array(target) * flip).tolist()
        lifted += 1
# Debris faces, matched by their seated centroid.
debris = st[tri[plan['delete_triangles']]].mean(1) * flip
kd = KDTree(len(debris))
for i, c in enumerate(debris):
    kd.insert(c, i)
kd.balance()
doomed = [f for f in bm.faces if kd.find(f.calc_center_median())[2] < 1e-4]
bmesh.ops.delete(bm, geom=doomed, context='FACES')
bm.to_mesh(me)
bm.free()
me.update()
report = {'seated': seat, 'lifted_vertices': lifted, 'deleted_faces': len(doomed),
          'planned_deletions': len(plan['delete_triangles'])}
print('A762_REBAKE_PREP', json.dumps(report), flush=True)

for other in scene.objects:
    other.hide_render = other is not ob
report['vertex_pass'] = B.vertex_masks(ob)
image = bpy.data.images.new('T_A762_WS_Mask_bake', B.MAIN_RES, B.MAIN_RES, alpha=True, float_buffer=True)
image.colorspace_settings.name = 'Non-Color'
B.bake(ob, image, 'UV1')
report['mask'] = B.finish(image, B.OUT / 'T_A762_WS_Mask.png', B.NEUTRAL_UV1)
(B.OUT / 'rebake_seated_report.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
print('A762_REBAKE_DONE', json.dumps(report), flush=True)
