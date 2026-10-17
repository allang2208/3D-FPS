from pathlib import Path
import json
O=Path(__file__).parent;ns={'__file__':str(O/'author_left_arm.py')};exec(compile((O/'author_left_arm.py').read_text().split('tree=ast.parse')[0],str(O/'author_left_arm.py'),'exec'),ns)
from mathutils import Matrix
original={n:Matrix(m) for n,m in json.loads((O/'before_diagnosis.json').read_text())['idle'].items()};out=ns['solve'](original,ns['frames'](original)[2]);(O/'surface_pose.json').write_text(json.dumps({n:[list(v) for v in m] for n,m in out.items()}))
