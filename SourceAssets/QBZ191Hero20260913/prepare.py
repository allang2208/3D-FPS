"""Read authoring inputs for the QBZ surface rebuild, without a preview run."""
import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent; S=O.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'QBZ191MagazineSeat20260913/QBZ191_MagazineSeat_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima']; inv=r.data.bones['WPN_root'].matrix_local.inverted()
out={'objects':{},'rails':{}}
for name in ['QBZ191_Export','QBZ191_Magazine_Export','SM_QBZ191_RearSight','SM_QBZ191_FrontSight']:
 ob=bpy.data.objects[name]
 out['objects'][name]={'materials':[m.name for m in ob.data.materials], 'vertices':len(ob.data.vertices),'modifiers':[(m.name,m.type) for m in ob.modifiers]}
with bpy.data.libraries.load(str(S/'QBZ19120260912/SourceInspect.blend'),link=False) as (a,b):b.objects=['QBZ']
raw=b.objects[0]; saved=json.loads((S/'QBZ19120260912/components.json').read_text())[0]; comps=saved['components']; source_world=Matrix(saved['matrix'])
out['source_normals']=raw.data.has_custom_normals
out['source_matrix']=[list(row) for row in raw.matrix_world]
for i in [21,22]:
 ids=set(comps[i]['ids']); faces=[]
 for f in raw.data.polygons:
  if all(v in ids for v in f.vertices):
   vs=[source_world@raw.data.vertices[v].co+Vector((-.005,-.11,.065)) for v in f.vertices]
   if max(v.z for v in vs)-min(v.z for v in vs)<.00001 and sum(v.z for v in vs)/len(vs)>.089:
    faces.append({'v':[[round(x,7) for x in v] for v in vs]})
 out['rails'][str(i)]=faces
(O/'author_inputs.json').write_text(json.dumps(out,indent=2))
print('AUTHOR_INPUTS_SAVED',out['source_normals'],flush=True)
