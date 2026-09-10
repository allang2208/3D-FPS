"""Sample actual deformed glove surface against the M4 receiver silhouette.
This bounds the left-side release approach, not a whole-mesh collision proof.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
hand=bpy.data.objects['SK_Manny_Arms_Export'];body=bpy.data.objects['M4_M4 Body_Export']
ids=[v.index for v in hand.data.vertices if sum(g.weight for g in v.groups if hand.vertex_groups[g.group].name.endswith('_l') and hand.vertex_groups[g.group].name.startswith(('hand','thumb','index','middle','ring','pinky')))>0.7]
a=bpy.data.actions['M4_MAT_reload_empty'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
samples=[]
for t in [i*.5 for i in range(240,275)]:
 s.frame_set(int(t),subframe=t-int(t));bpy.context.view_layer.update();dep=bpy.context.evaluated_depsgraph_get();inv=r.pose.bones['WPN_root'].matrix.inverted()
 b=body.evaluated_get(dep);bm=b.to_mesh();tree=BVHTree.FromPolygons([inv@b.matrix_world@v.co for v in bm.vertices],[list(p.vertices) for p in bm.polygons]);b.to_mesh_clear()
 h=hand.evaluated_get(dep);hm=h.to_mesh();points=[inv@h.matrix_world@hm.vertices[i].co for i in ids];h.to_mesh_clear()
 margin=999;checked=0
 for p in points:
  if not (-.165<p.y<.03 and -.01<p.z<.105):continue
  surface,normal,face,distance=tree.ray_cast(Vector((.15,p.y,p.z)),Vector((-1,0,0)),.19)
  if surface is not None and surface.x>-.005:margin=min(margin,(p.x-surface.x)*1000);checked+=1
 goal=Vector((.0185,-.0934,.055));nearest=min((p-goal).length for p in points)*1000
 samples.append({'source_time':t/60,'receiver_side_margin_mm':margin,'nearest_catch_surface_mm':nearest,'vertices_tested':checked})
report={'scope':'Actual deformed glove vertices; receiver left-side approach at 120 Hz, 2.0-2.2833 s. Not a whole-character collision test.','samples':samples,'minimum_margin_mm':min(p['receiver_side_margin_mm'] for p in samples),'contact_at_130':next(p for p in samples if abs(p['source_time']-130/60)<.0001)}
(O/'surface_validation.json').write_text(json.dumps(report,indent=2));print('SURFACE_RESULT',report['minimum_margin_mm'],report['contact_at_130'])
assert report['minimum_margin_mm']>-.5,report['minimum_margin_mm']
assert report['contact_at_130']['nearest_catch_surface_mm']<2,report['contact_at_130']
