import bpy,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/M1911Integration20260913')
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4TacticalToss20260910/M4_Hand_MAT_Editable.blend')
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
out={'actions':[{ 'name':a.name,'range':list(a.frame_range)} for a in bpy.data.actions],'fps':s.render.fps,'poses':{}}
for kind,action,f in [('idle','M4_idle',0),('mag','M4_MAT_reload',95),('charge','M4_MAT_equip_charge',16)]:
 a=bpy.data.actions.get(action)
 if not a:continue
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);bpy.context.view_layer.update();root=r.pose.bones['WPN_root'].matrix.inverted()
 out['poses'][kind]={b.name:[list(x) for x in root@b.matrix] for b in r.pose.bones}
(O/'manny_reference.json').write_text(json.dumps(out,indent=2))
for kind,p in out['poses'].items():
 print(kind,json.dumps({n:[round(x,4) for x in [p[n][i][3] for i in range(3)]] for n in ['hand_r','hand_l','index_01_r','middle_01_r','pinky_01_r','thumb_03_r','middle_03_r','WPN_SOCKET_Magazine','WPN_RearSight']}))
print('actions',out['actions'])
