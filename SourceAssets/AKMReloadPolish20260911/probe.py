import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;B=O.parent/'AKMAttachments20260911';report={}
bpy.ops.wm.open_mainfile(filepath=str(B/'AKM_Attachments_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
for clip in ['idle','reload','reload_empty']:
 a=bpy.data.actions['AKM_Native_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);rest=r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones['WPN_SOCKET_Magazine'].matrix
 rows=[]
 for f in range(0,201,10):
  s.frame_set(f);root=r.pose.bones['WPN_root'].matrix;mag=root.inverted()@r.pose.bones['WPN_SOCKET_Magazine'].matrix;hand=root.inverted()@r.pose.bones['hand_l'].matrix
  rows.append({'f':f,'mag_delta':list(mag.translation-rest.translation),'hand':list(hand.translation),'mag':list(mag.translation),'index':[list(r.pose.bones['index_0'+str(i)+'_r'].matrix_basis.to_quaternion()) for i in [1,2,3]]})
 report[clip]=rows
(O/'probe.json').write_text(json.dumps(report,indent=2));print('PROBE_PASS')
