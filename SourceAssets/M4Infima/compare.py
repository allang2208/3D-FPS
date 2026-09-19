exec(open('D:/FPS3D/FPSGAME/SourceAssets/M4Infima/check_export.py').read().split("d=bpy.data.cameras.new")[0])
from mathutils import Matrix
arm=next(o for o in s.objects if o.name=='Armature');gun=next(o for o in s.objects if o.name=='SKEL_AssaultRifle')
a=bpy.data.actions['A_FP_AssaultRifle_Idle_Loop'];arm.animation_data.action=a;arm.animation_data.action_slot=a.slots[0]
a=bpy.data.actions['A_WEP_Reference'];gun.animation_data.action=a;gun.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update()
print('SOURCE_GUN',list(gun.pose.bones['Grip'].matrix),list(gun.data.bones['Grip'].matrix_local))
print('OUTPUT_GUN',list(rig.pose.bones['WPN_root'].matrix),list(rig.data.bones['WPN_root'].matrix_local))
print('SOURCE_CAMERA',list(s.camera.matrix_world))
