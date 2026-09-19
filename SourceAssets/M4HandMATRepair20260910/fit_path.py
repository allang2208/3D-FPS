import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
hand=bpy.data.objects['SK_Manny_Arms_Export'];body=bpy.data.objects['M4_M4 Body_Export'];ids=[v.index for v in hand.data.vertices if sum(g.weight for g in v.groups if hand.vertex_groups[g.group].name.endswith('_l') and hand.vertex_groups[g.group].name.startswith(('hand','thumb','index','middle','ring','pinky')))>0.7]
a=bpy.data.actions['M4_MAT_reload_empty'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];result={}
for f in range(104,151):
 s.frame_set(f);bpy.context.view_layer.update();dep=bpy.context.evaluated_depsgraph_get();inv=r.pose.bones['WPN_root'].matrix.inverted();ev=body.evaluated_get(dep);bm=ev.to_mesh();tree=BVHTree.FromPolygons([inv@ev.matrix_world@v.co for v in bm.vertices],[list(p.vertices) for p in bm.polygons]);ev.to_mesh_clear();ev=hand.evaluated_get(dep);hm=ev.to_mesh();points=[inv@ev.matrix_world@hm.vertices[i].co for i in ids];ev.to_mesh_clear();push=0
 for p in points:
  if not (-.165<p.y<.03 and -.01<p.z<.105):continue
  surface,normal,face,dist=tree.ray_cast(Vector((.15,p.y,p.z)),Vector((-1,0,0)),.19)
  if surface is not None and surface.x>-.005:push=max(push,surface.x+.0015-p.x)
 result[f]=push
(O/'release_path_clearance.json').write_text(json.dumps(result,indent=2));print('PATH_FIT',max(result.values()),result[130])
