import bpy,json
from pathlib import Path
P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(next((P/'Source').glob('*.fbx'))))
r={'meshes':[],'images':[],'materials':[]}
for o in bpy.context.scene.objects:
 if o.type=='MESH':r['meshes'].append({'name':o.name,'dimensions':list(o.dimensions),'rotation':list(o.rotation_euler),'vertices':len(o.data.vertices),'triangles':sum(len(f.vertices)-2 for f in o.data.polygons),'uvs':[u.name for u in o.data.uv_layers],'custom_normals':o.data.has_custom_normals})
for i in bpy.data.images:r['images'].append({'name':i.name,'path':i.filepath,'size':list(i.size),'packed':bool(i.packed_file)})
for m in bpy.data.materials:r['materials'].append({'name':m.name,'nodes':[(n.type,n.name) for n in m.node_tree.nodes] if m.use_nodes else []})
(P/'report.json').write_text(json.dumps(r,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Imported.blend'))
