import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Vertical_Fitted.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
data=json.loads((O/'fit_final.json').read_text());G=Matrix(data['grip_matrix']);inv=G.inverted()
for d in ['index','middle','ring','pinky']:
 for j,a in enumerate([45,70,35],1):r.pose.bones[f'{d}_{j:02}_l'].rotation_quaternion=Quaternion((0,0,1),math.radians(a))
bpy.context.view_layer.update()
report={d:[list(inv@r.pose.bones[f'{d}_{j:02}_l'].head) for j in [1,2,3]]+[list(inv@r.pose.bones[f'{d}_03_l'].tail)] for d in ['index','middle','ring','pinky']}
print(json.dumps(report,indent=2));(O/'fist_points.json').write_text(json.dumps(report,indent=2))

H=r.pose.bones['hand_l'].matrix.copy();H.translation+=G.to_3x3()@Vector((.027,-.008,-.006));r.pose.bones['hand_l'].matrix=H;bpy.context.view_layer.update()
data['hand_in_root']=[list(row) for row in r.pose.bones['WPN_root'].matrix.inverted()@H]
for b in r.pose.bones:
 if b.name.startswith(('index','middle','ring','pinky','thumb')):data['basis'][b.name]=[list(row) for row in b.matrix_basis]
(O/'fit_final.json').write_text(json.dumps(data,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Vertical_Fitted.blend'))
