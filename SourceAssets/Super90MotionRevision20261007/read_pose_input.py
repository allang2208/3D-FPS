import bpy,json
from pathlib import Path
p=Path('D:/FPS3D/FPSGAME/SourceAssets')
bpy.ops.wm.open_mainfile(filepath=str(p/'BenelliM4Super9020261006/Super90_Gameplay_Editable.blend'))
r=bpy.data.objects['SK_Super90']; r.animation_data.action=bpy.data.actions['A_Super90_idle']; r.animation_data.action_slot=r.animation_data.action.slots[0]
bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
names=['hand_l','hand_r','upperarm_l','lowerarm_l','WPN_root','WPN_FrontSight','WPN_RearSight','WPN_BoltCatch','WPN_Load']
print('SOURCE_POSE',json.dumps({n:{'pos':list(r.pose.bones[n].matrix.translation),'quat':list(r.pose.bones[n].matrix.to_quaternion()),'rest':list(r.data.bones[n].matrix_local.translation)} for n in names}),flush=True)
