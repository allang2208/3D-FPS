import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path('D:/FPS3D/FPSGAME/SourceAssets/AngledForegrip20260910/GameIntegration')
bpy.ops.wm.open_mainfile(filepath=str(O/'A_M4_Foregrip_idle.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0);bpy.context.view_layer.update()
f=json.loads((O/'fit_final.json').read_text());G=r.pose.bones['WPN_root'].matrix@Matrix(f['grip_in_root'])
print('COORDS',json.dumps({n:[list(G.inverted()@getattr(r.pose.bones[n],p)) for p in ['head','tail']] for n in ['hand_l','index_01_l','index_02_l','index_03_l','middle_01_l','ring_01_l','pinky_01_l','pinky_02_l','pinky_03_l','thumb_03_l']}))
print('PARTS',[(o.name,list(o.dimensions)) for o in s.objects if o.name.startswith('FG_')])
