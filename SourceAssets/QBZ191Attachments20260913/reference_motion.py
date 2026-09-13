import bpy,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent;data={}
for kind,path in [('equip_charge','M4WrapGrip20260910'),('reload','M4TacticalToss20260910')]:
 bpy.ops.wm.open_mainfile(filepath=str(S/path/'M4_Hand_MAT_Editable.blend'))
 r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;a=bpy.data.actions['M4_MAT_'+kind];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 samples={}
 for f in range(int(a.frame_range[1])+1):
  s.frame_set(f);bpy.context.view_layer.update();samples[str(f)]={n:[list(v) for v in r.pose.bones[n].matrix] for n in ['WPN_root','WPN_SOCKET_Magazine','WPN_ChargingHandle','hand_l','hand_r']}
 data[kind]={'source':path,'action':a.name,'range':list(a.frame_range),'fps':s.render.fps,'samples':samples}
(O/'m4_reference_motion.json').write_text(json.dumps(data));print('M4_REFERENCE_MOTION_READ')
