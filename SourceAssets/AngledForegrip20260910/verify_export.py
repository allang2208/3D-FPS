import bpy,bmesh,json
from pathlib import Path
p=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(p/'AngledForegrip_M4.glb'))
report=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 bm=bmesh.new();bm.from_mesh(o.data)
 # GLB splits vertices at UV seams and hard normals; weld for geometric topology audit.
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
 report.append({'name':o.name,'vertices':len(bm.verts),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-12 for f in bm.faces),'uv':len(o.data.uv_layers)>0,'materials':[m.name for m in o.data.materials]})
 bm.free()
result={'objects':report,'all_have_uv':all(o['uv'] for o in report),'nonmanifold_edges':sum(o['nonmanifold_edges'] for o in report),'zero_area_faces':sum(o['zero_area_faces'] for o in report)}
(p/'export_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='objects'}))
