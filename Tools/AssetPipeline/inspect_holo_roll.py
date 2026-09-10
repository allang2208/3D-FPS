import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
import math
out=Path('D:/FPS3D/FPSGAME/SourceAssets/M4Holographic20260909')
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4InfimaRigRepair20260909/SK_M4_Infima_RigRepair.blend')
rig=bpy.data.objects['SK_M4_Infima']
result={}
for name in ['WPN_root','WPN_RearSight','WPN_FrontSight']:
 b=rig.data.bones[name];result[name]={'rest':[list(row) for row in b.matrix_local]}
result['actions']=[a.name for a in bpy.data.actions if 'aim' in a.name.lower()]
rear=rig.data.bones['WPN_RearSight'].matrix_local
front=rig.data.bones['WPN_FrontSight'].matrix_local
root=rig.data.bones['WPN_root'].matrix_local
axis=(front.translation-rear.translation).normalized()
old_up=(Vector((0,0,1))-axis*axis.z).normalized()
rail_up=rear.to_quaternion()@Vector((0,0,1))
result['legacy_mount_vs_rail_degrees']=math.degrees(old_up.angle(rail_up))
rig.animation_data_create();a=bpy.data.actions['M4_aim'];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
animated_up=rig.pose.bones['WPN_root'].matrix.to_quaternion()@(root.to_quaternion().inverted()@old_up)
result['legacy_aim_optic_up']=list(animated_up)
result['legacy_aim_cant_degrees']=math.degrees(math.atan2(animated_up.x,animated_up.z))
(out/'roll-source.json').write_text(json.dumps(result,indent=2))
