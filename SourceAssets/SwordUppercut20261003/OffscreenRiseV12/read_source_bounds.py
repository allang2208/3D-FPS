import bpy,json
from mathutils import Vector
p=r"D:/FPS3D/FPSGAME/SourceAssets/SwordUppercut20261003/IdleLeftV11/Standard/Sword_UppercutV11_Editable.blend"
bpy.ops.wm.open_mainfile(filepath=p)
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
print('RIG_OBJECT',rig.matrix_world)
for n in ('SK_RuneSword_Rig','VM_Root','root','hand_l','WPN_root'):
 if n in rig.data.bones:print('BONE',n,'rest',rig.data.bones[n].matrix_local,'pose',rig.pose.bones[n].matrix)
for o in bpy.context.scene.objects:
 if o.type=='MESH':print('MESH_MATRIX',o.matrix_world)
