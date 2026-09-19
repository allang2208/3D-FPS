import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Vertical_Fitted.blend'));r=bpy.data.objects['SK_M4_Infima'];data=json.loads((O/'fit_final.json').read_text());G=Matrix(data['grip_matrix'])
for d in ['index','middle','ring','pinky']:
 for j,a in enumerate([35,60,30],1):r.pose.bones[f'{d}_{j:02}_l'].rotation_quaternion=Quaternion((0,0,1),math.radians(a))
bpy.context.view_layer.update();pivot=r.pose.bones['middle_01_l'].head.copy();rotation=G.to_3x3()@Matrix.Rotation(math.radians(-18),3,'Y')@G.to_3x3().inverted();H=Matrix.Translation(pivot)@rotation.to_4x4()@Matrix.Translation(-pivot)@r.pose.bones['hand_l'].matrix;r.pose.bones['hand_l'].matrix=H;bpy.context.view_layer.update()
data['hand_in_root']=[list(row) for row in r.pose.bones['WPN_root'].matrix.inverted()@H]
for b in r.pose.bones:
 if b.name.startswith(('index','middle','ring','pinky','thumb')):data['basis'][b.name]=[list(row) for row in b.matrix_basis]
(O/'fit_final.json').write_text(json.dumps(data,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Vertical_Fitted.blend'))
