import json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;f=json.loads((O/'fit_final.json').read_text());G=Matrix(f['grip_in_root']);H=Matrix(f['hand_in_root']);H.translation+=G.to_3x3()@Matrix.Rotation(math.radians(45),3,'X')@Vector((0,0,-.010));f['hand_in_root']=[list(r) for r in H];f['hand_axial_slide_m']=.010;(O/'fit_final.json').write_text(json.dumps(f,indent=2))
