import bpy,json,pathlib
from mathutils import Vector
O=pathlib.Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4TacticalToss20260910/M4_Hand_MAT_Editable.blend')
r=bpy.data.objects['SK_M4_Infima'];hands=bpy.data.objects['SK_Manny_Arms_Export'];a=bpy.data.actions['M4_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
ev=hands.evaluated_get(bpy.context.evaluated_depsgraph_get());points=[r.matrix_world.inverted()@ev.matrix_world@v.co for v in ev.data.vertices];out={}
for side in ['l','r']:
 for digit in ['thumb','index','middle','ring','pinky']:
  n=f'{digit}_03_{side}';index=hands.vertex_groups[n].index
  candidates=[points[v.index] for v in hands.data.vertices if any(g.group==index and g.weight>.65 for g in v.groups)]
  origin=r.pose.bones[n].matrix.translation;previous=r.pose.bones[f'{digit}_02_{side}'].matrix.translation
  candidates.sort(key=lambda p:(p-previous).length,reverse=True)
  tip=sum(candidates[:max(4,len(candidates)//8)],Vector())/max(4,len(candidates)//8)
  local=r.pose.bones[n].matrix.inverted()@tip
  out[n]={'local_tip':list(local),'bone_length':r.data.bones[n].length,'vertices':len(candidates)}
(O/'fingertips.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
