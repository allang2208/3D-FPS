import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Integration/M4_Vertical_Fitted.blend'));r=bpy.data.objects['SK_M4_Infima'];data=json.loads((O.parent/'Integration/fit_final.json').read_text());sol=json.loads((O/'fist_solution.json').read_text());rest=r.data.bones
for n in ['hand_l']+[n for n in sol['pose'] if n.endswith('_l') and n.startswith(('index','middle','ring','pinky','thumb'))]:
 b=r.pose.bones[n];b.matrix=Matrix(sol['pose'][n]);bpy.context.view_layer.update()
data['hand_in_root']=[list(row) for row in r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones['hand_l'].matrix]
for b in r.pose.bones:
 if b.name.startswith(('index','middle','ring','pinky','thumb')):data['basis'][b.name]=[list(row) for row in b.matrix_basis]
(O/'fit_final.json').write_text(json.dumps(data,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Vertical_Fitted.blend'))
