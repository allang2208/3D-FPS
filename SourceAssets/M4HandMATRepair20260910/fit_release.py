import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix,Euler
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;a=bpy.data.actions['M4_MAT_reload_empty'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(130);bpy.context.view_layer.update()
dep=bpy.context.evaluated_depsgraph_get();inv=r.pose.bones['WPN_root'].matrix.inverted();wrist=inv@r.pose.bones['hand_l'].head
hand=bpy.data.objects['SK_Manny_Arms_Export'];ev=hand.evaluated_get(dep);hm=ev.to_mesh()
ids=[v.index for v in hand.data.vertices if sum(g.weight for g in v.groups if hand.vertex_groups[g.group].name.endswith('_l') and hand.vertex_groups[g.group].name.startswith(('hand','thumb','index','middle','ring','pinky')))>0.7]
points=[inv@ev.matrix_world@hm.vertices[i].co for i in ids];ev.to_mesh_clear()
body=bpy.data.objects['M4_M4 Body_Export'].evaluated_get(dep);bm=body.to_mesh();vs=[inv@body.matrix_world@v.co for v in bm.vertices];polys=[list(p.vertices) for p in bm.polygons];tree=BVHTree.FromPolygons(vs,polys);body.to_mesh_clear()
goal=Vector((.0185,-.0934,.055));contact=min(points,key=lambda p:(p-goal).length)
results=[]
for ry in [-15,-10,-5,0,5,10,15]:
 for rz in [-15,-10,-5,0,5,10,15]:
  rot=Euler((0,math.radians(ry),math.radians(rz))).to_matrix();cp=wrist+rot@(contact-wrist);shift=goal-cp;push=0;hit=0
  for v in points[::4]:
   p=wrist+rot@(v-wrist)+shift
   if not (-.165<p.y<.03 and -.01<p.z<.105):continue
   surface,normal,face,distance=tree.ray_cast(Vector((.15,p.y,p.z)),Vector((-1,0,0)),.19)
   if surface is not None and surface.x>-.005:push=max(push,surface.x+.0008-p.x);hit+=1
  results.append({'ry':ry,'rz':rz,'shift':list(shift+Vector((push,0,0))),'contact_gap_mm':push*1000,'cost':push*1000+.02*(abs(ry)+abs(rz)),'vertices_checked':hit})
results.sort(key=lambda x:x['cost']);(O/'release_fit.json').write_text(json.dumps(results[:10],indent=2));print('CONTACT_FIT',json.dumps(results[:3]))

