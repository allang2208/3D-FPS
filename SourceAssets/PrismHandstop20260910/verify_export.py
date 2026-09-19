import bpy,bmesh,json
from pathlib import Path
P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(P/'PrismHandstop.glb'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(objects)==1
o=objects[0];bm=bmesh.new();bm.from_mesh(o.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
report={'mesh_count':len(objects),'triangles':len(bm.faces),'uv_layers':len(o.data.uv_layers),'zero_area_faces':sum(f.calc_area()<1e-14 for f in bm.faces),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'materials':[m.name for m in o.data.materials]}
(P/'export_validation.json').write_text(json.dumps(report,indent=2))
assert report['uv_layers']>0 and report['zero_area_faces']==0 and report['boundary_edges']==0,report
bm.free();print('PRISM_EXPORT_VERIFY_PASS')
