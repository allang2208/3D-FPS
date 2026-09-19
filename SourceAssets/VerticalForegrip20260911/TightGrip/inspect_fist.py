import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Quaternion
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Vertical_Fitted.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
data=json.loads((O/'fit_final.json').read_text());G=Matrix(data['grip_matrix']);inv=G.inverted()
for d in ['index','middle','ring','pinky']:
 for j,a in enumerate([45,70,35],1):r.pose.bones[f'{d}_{j:02}_l'].rotation_quaternion=Quaternion((0,0,1),math.radians(a))
bpy.context.view_layer.update()
report={d:[list(inv@r.pose.bones[f'{d}_{j:02}_l'].head) for j in [1,2,3]]+[list(inv@r.pose.bones[f'{d}_03_l'].tail)] for d in ['index','middle','ring','pinky']}
print(json.dumps(report,indent=2));(O/'fist_points.json').write_text(json.dumps(report,indent=2))
