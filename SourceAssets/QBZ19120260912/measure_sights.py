import bpy,json
from pathlib import Path
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'SourceInspect.blend'));o=bpy.data.objects['QBZ'];cs=json.loads((O/'components.json').read_text())[0]['components'];out={str(c):[list(o.matrix_world@o.data.vertices[i].co) for i in cs[c]['ids']] for c in [80,81,82,94]};(O/'sight_vertices.json').write_text(json.dumps(out))
