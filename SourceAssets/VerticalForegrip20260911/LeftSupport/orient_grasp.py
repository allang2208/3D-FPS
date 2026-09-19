import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;f=json.loads((O.parent/'WristNatural/fit_final.json').read_text());G=Matrix(f['grip_in_root']);R=Matrix.Rotation(math.radians(-25),4,'Z');H=G@R@G.inverted()@Matrix(f['hand_in_root']);f['hand_in_root']=[list(r) for r in H];f['release_vector']=list(R.to_3x3()@Vector(f['release_vector']));f['support_grasp_yaw_degrees']=-25;(O/'fit_final.json').write_text(json.dumps(f,indent=2))
