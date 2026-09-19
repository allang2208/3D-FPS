import bpy,json
from pathlib import Path
src=Path('D:/FPS3D/FPSGAME/SourceAssets/M4Infima')
bpy.ops.wm.open_mainfile(filepath=str(src/'M4_Infima_Candidate.blend'))
s=bpy.context.scene;a=bpy.data.objects['Armature'];g=bpy.data.objects['SKEL_AssaultRifle']
for obj,name in [(a,'A_FP_AssaultRifle_Reload'),(g,'A_FP_WEP_AssaultRifle_Reload')]:
 act=bpy.data.actions[name];obj.animation_data.action=act;obj.animation_data.action_slot=act.slots[0]
for f in [0,15,30,45,57,80,94]:
 s.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();ae=a.evaluated_get(dg);ge=g.evaluated_get(dg)
 print('SOURCE',f,'gun',list(g.matrix_world.translation),list(g.matrix_world.to_quaternion()),'evaluated',list(ge.matrix_world.translation),list(ge.matrix_world.to_quaternion()),'ik',list(a.pose.bones['ik_hand_gun'].matrix.translation),'ik_eval',list(ae.pose.bones['ik_hand_gun'].matrix.translation))
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4InfimaRigRepair20260909/SK_M4_Infima_RigRepair.blend')
r=bpy.data.objects['SK_M4_Infima'];act=bpy.data.actions['M4_reload'];r.animation_data_create();r.animation_data.action=act;r.animation_data.action_slot=act.slots[0]
for f in [0,30,60,90,114,160,188]:
 bpy.context.scene.frame_set(f);bpy.context.view_layer.update()
 print('EXPORT',f,[(n,list(r.pose.bones[n].matrix.translation),list(r.pose.bones[n].matrix.to_quaternion())) for n in ['WPN_root','ik_hand_gun','hand_r']])
