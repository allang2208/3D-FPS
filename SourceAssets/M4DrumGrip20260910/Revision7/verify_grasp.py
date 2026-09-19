import bpy,math,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_DrumMatch_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;report={}
def sample(name,t):
 a=bpy.data.actions[name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 s.frame_set(int(t),subframe=t%1);bpy.context.view_layer.update()
 w=r.pose.bones['WPN_root'].matrix.inverted()
 return {b.name:w@b.matrix for b in r.pose.bones if b.name.endswith('_l')}
for clip,start,end in [('reload',50,98),('reload_empty',43,88)]:
 pos=angle=0
 for k in range(start*2,end*2+1):
  a=sample('A_M4_DrumMatch_'+clip,k/2);b=sample('BeforeMatch_'+clip,k/2)
  for n in a:
   pos=max(pos,(a[n].translation-b[n].translation).length*100)
   q=math.degrees(a[n].to_quaternion().rotation_difference(b[n].to_quaternion()).angle)
   angle=max(angle,min(q,360-q))
 report[clip]={'start':start,'end':end,'position_error_cm':pos,'angle_error_deg':angle}
 assert pos<.005 and angle<.06,report
(O/'grasp_contract.json').write_text(json.dumps(report,indent=2));print(report)
