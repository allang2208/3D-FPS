import bpy,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/MannyGraspDonor20260912')
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/VerticalGripFront20260911/m4/vertical/A_M4_Vertical_idle.blend')
r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(0)
names=['hand_l','lowerarm_l']+[b.name for b in r.pose.bones if b.name.startswith(('thumb','index','middle','ring','pinky')) and b.name.endswith('_l')]
data={'world':[list(x) for x in r.matrix_world],'bones':{n:{'parent':r.pose.bones[n].parent.name,'rest':[list(x) for x in r.data.bones[n].matrix_local],'pose':[list(x) for x in r.pose.bones[n].matrix]} for n in names}}
(O/'target_reference.json').write_text(json.dumps(data,indent=2))
print('TARGET_REFERENCE_READY',r.matrix_world,flush=True)
