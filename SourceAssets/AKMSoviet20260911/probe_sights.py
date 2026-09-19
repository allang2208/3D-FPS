import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'SourceInspect.blend'));o=bpy.data.objects['AK'];g=json.loads((O/'components.json').read_text())
for i in [6,7,25]:
 pts=[o.matrix_world@o.data.vertices[v].co for v in g[i]['ids']];p=[list(v) for v in pts if abs(v.x)<.0035];print('SIGHT',i,json.dumps(p))
