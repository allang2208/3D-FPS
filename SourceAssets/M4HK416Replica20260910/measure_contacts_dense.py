import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_HK416_Adapted_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;hand=bpy.data.objects['SK_Manny_Arms_Export'];body=bpy.data.objects['M4_M4 Body_Export']
ids=[v.index for v in hand.data.vertices if sum(g.weight for g in v.groups if hand.vertex_groups[g.group].name.endswith('_l') and hand.vertex_groups[g.group].name.startswith(('hand','thumb','index','middle','ring','pinky')))>0.7]
report={}
for clip,frames in [('reload_empty',list(range(120,138))),('reload',[29,50,76,95]),('equip_charge',[9,15,22,30])]:
 a=bpy.data.actions['M4_HK416_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];result=[]
 for t in frames:
  s.frame_set(t);bpy.context.view_layer.update();dep=bpy.context.evaluated_depsgraph_get();obj=hand.evaluated_get(dep);m=obj.to_mesh();inv=r.pose.bones['WPN_root'].matrix.inverted()
  points=[inv@obj.matrix_world@m.vertices[i].co for i in ids];inside=[p for p in points if -.14<p.y<-.06 and .02<p.z<.095]
  result.append({'frame':t,'hand_local':list(inv@r.pose.bones['hand_l'].head),'finger_tips':{n:list(inv@r.pose.bones[n+'_03_l'].tail) for n in ['thumb','index','middle','ring','pinky']},'receiver_slab_vertices':len(inside),'min_side_cm':min([p.x*100 for p in inside],default=999)})
  obj.to_mesh_clear()
 report[clip]=result
(O/'contacts.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

