import bpy
p='D:/FPS3D/FPSGAME/SourceAssets/M4AnimationAudit20260910/M4_Hand_MAT_Editable.blend';bpy.ops.wm.open_mainfile(filepath=p);r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['M4_MAT_reload_empty'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
for f in [0,21,28,29,35,39,44]:
 bpy.context.scene.frame_set(f);bpy.context.view_layer.update();print(f,{n:list(r.pose.bones[n].matrix.translation) for n in ['WPN_root','WPN_SOCKET_Magazine','hand_l']})
