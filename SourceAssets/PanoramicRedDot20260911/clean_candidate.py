import bpy,bmesh,json,struct
from pathlib import Path
P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(next(P.glob('*textured_master*.glb'))))
o=next(o for o in bpy.context.scene.objects if o.type=='MESH');o.name='PanoramicRedDot_5080_CleanCandidate'
bm=bmesh.new();bm.from_mesh(o.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
# The generated background slab shares vertices with the bottom of the housing.
# Remove only its bottom slice, then cap the new horizontal cut.
cut=-.213
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=(0,0,cut),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
remaining=set(bm.verts);islands=[]
while remaining:
 seed=remaining.pop();part={seed};todo=[seed]
 while todo:
  v=todo.pop()
  for edge in v.link_edges:
   w=edge.other_vert(v)
   if w in remaining:remaining.remove(w);part.add(w);todo.append(w)
 islands.append(part)
keep=max(islands,key=len)
remove=[v for part in islands if part is not keep for v in part]
bmesh.ops.delete(bm,geom=remove,context='VERTS')
edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-cut)<.00001 for v in e.verts)]
if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(o.data);bm.free();o.data.update()
mat=bpy.data.materials.new('Graphite_preview');mat.use_nodes=True
bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.055,.065,.075,1);bs.inputs['Metallic'].default_value=.65;bs.inputs['Roughness'].default_value=.43
o.data.materials.clear();o.data.materials.append(mat)
for poly in o.data.polygons:poly.material_index=0
bpy.context.view_layer.objects.active=o;o.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'panoramic_red_dot_clean_editable.blend'))
bpy.ops.export_scene.gltf(filepath=str(P/'panoramic_red_dot_clean.glb'),export_format='GLB',use_selection=True)
bpy.ops.export_scene.fbx(filepath=str(P/'panoramic_red_dot_clean.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False)
o.data.calc_loop_triangles()
raw=next(P.glob('*raw_geometry*.glb'))
with raw.open('rb') as f:
 f.read(12);length,kind=struct.unpack('<II',f.read(8));doc=json.loads(f.read(length))
rawtri=sum(doc['accessors'][p['indices']]['count']//3 for m in doc['meshes'] for p in m['primitives'])
report={'raw_triangles':rawtri,'textured_master_triangles':93387,'clean_triangles':len(o.data.loop_triangles),'removed_loose_components':len(islands)-1,'cut_z':cut,'material':'Local constant graphite preview; generated textured original retained','limitations':['Generated housing details remain soft; not hard-surface retopology','No functional optical glass or game reticle; not integrated into game','Normalized generator units, final mounting dimensions not calibrated']}
(P/'cleanup_report.json').write_text(json.dumps(report,indent=2));print('CLEAN_CANDIDATE_PASS',json.dumps(report))
