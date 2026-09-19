import bpy,json
from pathlib import Path
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'AKMSoviet20260911/AKM_Soviet_Editable.blend'))
o=bpy.data.objects['AKM_Soviet_Native'];counts={g.name:sum(any(a.group==g.index and a.weight>.01 for a in v.groups) for v in o.data.vertices) for g in o.vertex_groups};print('WEIGHT_COUNTS',json.dumps({k:v for k,v in counts.items() if v}));print('MATERIALS',[(m.name,sum(f.material_index==i for f in o.data.polygons)) for i,m in enumerate(o.data.materials)]);print('MODIFIERS',[(m.name,m.type) for m in o.modifiers]);print('CHILDREN',[(c.name,c.type) for c in o.children])
