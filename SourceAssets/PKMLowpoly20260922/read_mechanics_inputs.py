import bpy,json,pathlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=pathlib.Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Refinement01'/'PKM_Lowpoly_Refined.blend'))
parts={o['source_part_id']:o for o in bpy.context.scene.objects if o.type=='MESH'}
report={'surface_samples':{},'cartridges':[],'links':[]}
for idx in [42,43]:
 o=parts[idx];vs=[o.matrix_world@v.co for v in o.data.vertices];bvh=BVHTree.FromPolygons(vs,[tuple(p.vertices) for p in o.data.polygons])
 rows=[]
 for y in [-.008,.02,.06,.10,.16,.22,.27]:
  for x in [-.014,0,.014]:
   hit=bvh.ray_cast(Vector((x,y,-.2 if idx==43 else .2)),Vector((0,0,1 if idx==43 else -1)),.5)
   rows.append({'xy':[x,y],'z':hit[0].z if hit[0] else None})
 report['surface_samples'][idx]=rows
for idx in list(range(0,42,3))+[69,113,114,115,116,117,118,119,120,121,122,123,124,125,126]:
 o=parts[idx];v=[o.matrix_world@p.co for p in o.data.vertices];c=[(min(p[a] for p in v)+max(p[a] for p in v))*.5 for a in range(3)]
 report['cartridges' if idx<42 else 'links'].append({'id':idx,'center':c})
(ROOT/'mechanics_inputs.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
