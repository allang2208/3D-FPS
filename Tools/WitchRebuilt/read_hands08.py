import bpy,json
from pathlib import Path
from mathutils import Vector
root=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');out=root/'Revision08';out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(root/'Authoring/WitchRebuilt_Idle.blend'))
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');bpy.context.scene.frame_set(1)
rest={b.name:r.matrix_world@b.matrix_local for b in r.data.bones};result={}
for side in ('l','r'):
 h=rest['hand_'+side];along=(rest['middle_01_'+side].translation-h.translation).normalized();across=(rest['index_01_'+side].translation-rest['pinky_01_'+side].translation).normalized();cross=along.cross(across).normalized()
 inv=h.inverted();current=r.matrix_world@r.pose.bones['hand_'+side].matrix
 def coord(p):
  d=p-h.translation;return [round(d.dot(x)*100,4) for x in (along,across,cross)]
 result[side]={'rest_axes':[list(v) for v in (along,across,cross)],'rest':{},'current_in_reference_hand_frame':{}}
 for finger in ('index','middle','ring','pinky','thumb'):
  for j in (1,2,3):
   n=f'{finger}_{j:02d}_{side}';result[side]['rest'][n]=coord(rest[n].translation)
   p=h@current.inverted()@(r.matrix_world@r.pose.bones[n].matrix).translation
   result[side]['current_in_reference_hand_frame'][n]=coord(p)
 result[side]['reference_thumb_signed_cross_cm']=result[side]['rest']['thumb_02_'+side][2]
 result[side]['current_hand_axes_world']=[list(current.to_quaternion()@h.to_quaternion().inverted()@v) for v in (along,across,cross)]
(out/'hand_inputs.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
