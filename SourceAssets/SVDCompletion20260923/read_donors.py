import bpy,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923');S=O.parent
result={}
for key,file in [('akm',S/'AKMSoviet20260911/AKM_Soviet_Editable.blend'),('m4',S/'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(file));r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['AKM_Native_idle'] if key=='akm' else r.animation_data.action;r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();inv=r.pose.bones['WPN_root'].matrix.inverted()
 result[key]={'actions':{x.name:list(x.frame_range) for x in bpy.data.actions},'fps':bpy.context.scene.render.fps,'rest':{n:[list(x) for x in r.data.bones[n].matrix_local] for n in ['WPN_root','hand_l','hand_r']},'bones':{n:list((inv@r.pose.bones[n].matrix).translation) for n in ['hand_l','hand_r','WPN_SOCKET_Muzzle','WPN_SOCKET_Magazine','WPN_bolt']},'meshes':[o.name for o in bpy.context.scene.objects if o.type=='MESH']}
(O/'donors.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
