import bpy,json
from pathlib import Path
p=Path('D:/FPS3D/FPSGAME/SourceAssets/RuneSword20260913/InspectForwardSpinV54/AzureRunesword_InspectForwardSpinV79.blend')
bpy.ops.wm.open_mainfile(filepath=str(p))
r=bpy.data.objects['SK_RuneSword_Rig']; a=bpy.data.objects['SK_Manny_Arms_Export']
with bpy.data.libraries.load('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/RuneSword_BareArmsV7.blend') as (src,dst):dst.objects=src.objects
n=next(o for o in dst.objects if o and o.type=='ARMATURE');m=next(o for o in dst.objects if o and o.type=='MESH')
print('OBJECTS',[(o.name,list(o.matrix_world.translation),list(o.scale)) for o in (r,a,n,m)])
for name in ['root','hand_r','index_01_r','middle_01_r','lowerarm_r','upperarm_r','WPN_root']:
 if name not in n.data.bones:continue
 print(name,'SOURCE',list(r.data.bones[name].matrix_local.translation),list(r.data.bones[name].matrix_local.to_quaternion()),'NATIVE',list(n.data.bones[name].matrix_local.translation),list(n.data.bones[name].matrix_local.to_quaternion()))
print('BOUNDS',[(o.name,[(min(v.co[i] for v in o.data.vertices),max(v.co[i] for v in o.data.vertices)) for i in range(3)]) for o in (a,m)])

bpy.context.scene.frame_set(0)
w=r.pose.bones["WPN_root"].matrix
h=r.pose.bones["hand_r"].matrix
cp=h @ __import__("mathutils").Vector((-0.08261,-0.03838,-0.0315))
print("CONTACT_WPN",list(w.inverted()@cp),"HAND_WPN",list(w.inverted()@h.translation))
