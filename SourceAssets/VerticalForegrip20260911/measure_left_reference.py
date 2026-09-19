import bpy,json,math
from pathlib import Path
from mathutils import Matrix
O=Path('D:/FPS3D/FPSGAME/SourceAssets/VerticalForegrip20260911/LeftSupport');O.mkdir(exist_ok=True);out={}
for kind,path in [('vertical',O.parent/'WristNatural/A_M4_Vertical_idle.blend'),('prism',O.parents[1]/'PrismHandstop20260910/GripAnimation/A_M4_Prism_idle.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;s.frame_set(0);r=bpy.data.objects['SK_M4_Infima'];bpy.context.view_layer.update();G=r.pose.bones['WPN_root'].matrix@Matrix(json.loads((O.parent/'WristNatural/fit_final.json').read_text())['grip_in_root']);out[kind]={n:list(G.inverted()@r.pose.bones[n].head) for n in ['clavicle_l','upperarm_l','lowerarm_l','hand_l']}
(O/'reference_positions.json').write_text(json.dumps(out,indent=2));print(out)
