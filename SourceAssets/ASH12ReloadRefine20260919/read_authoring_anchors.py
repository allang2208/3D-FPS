import bpy, json
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/ASH1220260917/ASH12_Editable.blend')
r=bpy.data.objects['SK_M4_Infima']; a=bpy.data.actions['ASH12_idle'];r.animation_data.action=a
if a.slots:r.animation_data.action_slot=a.slots[0]
bpy.context.scene.frame_set(0);bpy.context.view_layer.update(); inv=r.pose.bones['WPN_root'].matrix.inverted()
data={}
for n in ['WPN_root','WPN_SOCKET_Magazine','WPN_ChargingHandle','WPN_bolt','upperarm_r','lowerarm_r','hand_r','index_01_r','index_02_r','index_03_r','middle_01_r','upperarm_l','lowerarm_l','hand_l']:
 p=inv@r.pose.bones[n].matrix;data[n]={'p':list(p.translation),'q':list(p.to_quaternion())}
g=bpy.data.objects['ASH12_Export']; rest_inv=r.data.bones['WPN_root'].matrix_local.inverted()
for name in ['WPN_SOCKET_Magazine','WPN_ChargingHandle']:
 group=g.vertex_groups[name];pts=[rest_inv@(g.matrix_world@v.co) for v in g.data.vertices if any(k.group==group.index and k.weight>.5 for k in v.groups)]
 data[name]['geometry']={'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)]}
Path('D:/FPS3D/FPSGAME/SourceAssets/ASH12ReloadRefine20260919/anchors.json').write_text(json.dumps(data,indent=2))
print('AUTHORING_ANCHORS',json.dumps(data))
print('FINGER_LOCAL', {n: [round(x*180/3.14159265,1) for x in r.pose.bones[n].rotation_quaternion.to_euler('XYZ')] for n in r.pose.bones.keys() if n.endswith('_r') and n.startswith(('index_','middle_','ring_','pinky_','thumb_'))})
