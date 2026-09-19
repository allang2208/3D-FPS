"""Read the original mounting surfaces for grip production; no rendering."""
import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'FrostSwordModules20260915/FrostSword_Modular_Editable.blend'))
obj=bpy.data.objects['SM_FrostSword_Grip_factory'];m=obj.data
bvh=BVHTree.FromPolygons([v.co for v in m.vertices],[list(p.vertices) for p in m.polygons])
rows=[]
for z in [0,-.002,-.006,-.01,-.015,-.02,-.03,-.045,-.06,-.085,-.11,-.135,-.15,-.16,-.167,-.172,-.177]:
    row={'z':z,'hits':[]}
    for d in [Vector((1,0,0)),Vector((-1,0,0)),Vector((0,1,0)),Vector((0,-1,0))]:
        hit=bvh.ray_cast(Vector((0,0,z)),d,.1)[0]
        row['hits'].append(list(hit) if hit else None)
    rows.append(row)
data={'location':list(obj.location),'materials':[x.name for x in m.materials], 'cross_sections':rows}
(P/'original_grip_inputs.json').write_text(json.dumps(data,indent=2))
print(json.dumps(data),flush=True)
