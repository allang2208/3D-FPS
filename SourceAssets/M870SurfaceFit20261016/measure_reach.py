import bpy,json,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M870_SurfaceFit_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene;auth=json.loads((O/'authoring.json').read_text())
rest={b.name:b.matrix_local.copy() for b in r.data.bones};f0=rest['hand_l'].translation-rest['lowerarm_l'].translation;l1=(rest['lowerarm_l'].translation-rest['upperarm_l'].translation).length
out={}
for role in ('idle','fire','cycle','reload_full','quick_melee'):
 a=bpy.data.actions[auth['clips'][role]['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];rows=[]
 for f in range(int(a.frame_range[1])+1):
  s.frame_set(f);p={b.name:b.matrix.copy() for b in r.pose.bones};w=p['hand_l'].translation;e=p['lowerarm_l'].translation;sh=p['upperarm_l'].translation
  dh=p['hand_l'].to_quaternion()@rest['hand_l'].to_quaternion().inverted();ideal=w-dh@f0;newa=ideal+(sh-ideal).normalized()*l1
  rows.append({'frame':f,'bend':math.degrees((dh@f0).angle(w-e)),'shift_mm':(newa-sh).length*1000,'shift':list(newa-sh)})
 out[role]=max(rows,key=lambda x:x['bend'])
(O/'reach_measurement.json').write_text(json.dumps(out,indent=2));print(out)
