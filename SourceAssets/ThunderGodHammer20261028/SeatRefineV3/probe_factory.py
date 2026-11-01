import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(P.parent/'ModulesV1/ThunderGodHammer_Modular_Editable.blend'),link=False) as(a,b):b.objects=['SM_ThunderGodHammer_head_mount_factory']
o=b.objects[0];bpy.context.collection.objects.link(o);m=o.data;m.calc_loop_triangles()
bvh=BVHTree.FromPolygons([v.co for v in m.vertices],[list(t.vertices) for t in m.loop_triangles],all_triangles=True)
grid={}
for z in [.85,.86,.87,.88,.89,.90,.91,.92,.93,.94,.95,.96,.97,.98,.99]:
 grid[z]=[]
 for x in [-.06,-.05,-.04,-.03,-.02,0,.02,.03,.04,.05,.06]:
  hit=bvh.ray_cast(Vector((x,-.2,z)),Vector((0,1,0)),.4)[0];grid[z].append(round(hit.y,4) if hit else None)
(P/'factory_surface_probe.json').write_text(json.dumps(grid,indent=2))
print('GRID',json.dumps(grid))
