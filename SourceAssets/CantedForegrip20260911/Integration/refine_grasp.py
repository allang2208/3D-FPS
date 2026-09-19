import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;f=json.loads((O/'fit_final.json').read_text());G=Matrix(f['grip_matrix']);pivot=Vector((0,0,-.014));T=Matrix.Translation(pivot)@Matrix.Rotation(math.radians(-45),4,'X')@Matrix.Translation(-pivot);R=Matrix.Rotation(math.radians(-15),4,'Z');D=G@T@R@T.inverted()@G.inverted();H=D@Matrix(f['hand_matrix']);root=Matrix(f['hand_matrix'])@Matrix(f['hand_in_root']).inverted();f['hand_matrix']=[list(r) for r in H];f['hand_in_root']=[list(r) for r in root.inverted()@H];f['release_vector']=list((T@R@T.inverted()).to_3x3()@Vector(f['release_vector']));f['grasp_axial_degrees']=-15
(O/'fit_final.json').write_text(json.dumps(f,indent=2))
