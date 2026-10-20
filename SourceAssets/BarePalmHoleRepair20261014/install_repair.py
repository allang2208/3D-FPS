"""Apply sparse palm patches to the current native meshes; preserve their binds."""
import json,hashlib,shutil,math
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BarePalmHoleRepair20261014'
Q=u.GeometryScript_MeshQueries;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;Ed=u.GeometryScript_MeshEdits
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);E=u.EditorAssetLibrary
(R/'SavedFinal').mkdir(exist_ok=True)
def xyz(v):return [v.x,v.y,v.z]
def rgba(v):return [v.r,v.g,v.b,v.a]
def average(rows):return [sum(x)/len(rows) for x in zip(*rows)]
def dynamic(asset):
 dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+asset.get_path_name())
 return dm
def bones_signature(dm):
 _,bones=B.get_all_bones_info(dm)
 return {str(b.name):[b.index,b.parent_index,xyz(b.world_transform.translation),
   [xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]] for b in bones}
plans=json.loads((R/'triangulated_plan.json').read_text())
for entry in plans:
 path=entry['path'];key=hashlib.sha256(path.split('.')[0].encode()).hexdigest()[:12];receipt=R/'SavedFinal'/(key+'.json')
 if receipt.exists():continue
 file=P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
 previous=json.loads((R/'Saved'/(key+'.json')).read_text())
 if hashlib.sha256(file.read_bytes()).hexdigest()!=previous['sha256']:raise RuntimeError('Asset changed since this repair: '+path)
 asset=u.load_asset(path)
 if asset.get_outermost() in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Retain unsaved edits: '+path)
 snapshot=json.loads(Path(entry['snapshot']).read_text());dm=dynamic(asset);before_bones=bones_signature(dm)
 current=json.loads((R/'After'/(key+'.json')).read_text())
 current_tri_ids=current.get('triangle_ids',list(range(len(current['triangles']))))
 def near(a,b):return sum((x-y)**2 for x,y in zip(a,b))<1e-8
 _,infos=B.get_all_bones_info(dm);bone_ids={str(b.name):b.index for b in infos}
 triangle_ids=snapshot.get('triangle_ids',list(range(len(snapshot['triangles']))))
 vertex_ids=snapshot.get('vertex_ids',list(range(len(snapshot['positions']))))
 uv_count=Q.get_num_uv_sets(dm)
 if uv_count>8:raise RuntimeError('Preserve unsupported UV channels '+path)
 _,old_ps,gaps=Q.get_all_vertex_positions(dm,False)
 if gaps:raise RuntimeError('Expected compact native vertex IDs')
 start=Q.get_vertex_count(dm);verts=[];normals=[];colors=[];uvs=[[] for i in range(uv_count)];faces=[];weights=[];materials=[];remove=set()
 for patch in entry['patches']:
  center_vertices={i for i,p in enumerate(current['positions']) if near(p,patch['center'])}
  fan_faces=[i for i,t in enumerate(current['triangles']) if any(v in center_vertices for v in t)]
  if len(fan_faces)!=len(patch['corners']):raise RuntimeError('Cannot identify previous local patch: '+path)
  boundary=[]
  for c in patch['corners']:
   source_vi=[snapshot['triangles'][c['triangle']][i] for i in (c['a'],c['b'])]
   positions=[snapshot['positions'][vi] for vi in source_vi]
   match=None
   for fi in fan_faces:
    tri=current['triangles'][fi];coords=[current['positions'][vi] for vi in tri]
    aa=next((i for i,p in enumerate(coords) if near(p,positions[0])),None)
    bb=next((i for i,p in enumerate(coords) if near(p,positions[1])),None)
    if aa is not None and bb is not None:match=(current_tri_ids[fi],aa,bb);break
   if match is None:raise RuntimeError('Cannot preserve palm perimeter attributes: '+path)
   ti,aa,bb=match
   _,n0,n1,n2,ok=Q.get_triangle_normals(dm,ti)
   if not ok:raise RuntimeError('Missing original split normal')
   _,c0,c1,c2,hascolor=Q.get_triangle_vertex_colors(dm,ti)
   original_normals=[xyz(v) for v in (n0,n1,n2)];original_colors=[rgba(v) for v in (c0,c1,c2)] if hascolor else [[0,0,0,1]]*3
   original_uv=[]
   for channel in range(uv_count):
    a,b,cuv,ok=Q.get_triangle_u_vs(dm,channel,ti)
    if not ok:raise RuntimeError('Missing original UV '+str(channel))
    original_uv.append([[v.x,v.y] for v in (a,b,cuv)])
   pair=[]
   for vi,ci in zip(source_vi,[aa,bb]):
    pair.append(dict(position=snapshot['positions'][vi],normal=original_normals[ci],color=original_colors[ci],
      uv=[layer[ci] for layer in original_uv],weights=snapshot['weights'][vi]))
   boundary.append(pair)
  for triangle in patch['fill_triangles']:
   index=len(verts);faces.append(u.IntVector(index,index+1,index+2));materials.append(patch['material'])
   for row in [boundary[i][0] for i in triangle]:
    verts.append(u.Vector(*row['position']));normals.append(u.Vector(*row['normal']));colors.append(u.LinearColor(*row['color']));weights.append(row['weights'])
    for ch in range(uv_count):uvs[ch].append(u.Vector2D(*row['uv'][ch]))
  remove.update(current_tri_ids[i] for i in fan_faces)
 kwargs=dict(vertices=verts,normals=normals,vertex_colors=colors,triangles=faces)
 for ch,layer in enumerate(uvs):kwargs['uv'+str(ch)]=layer
 _,old_indices,triangle_gaps=Q.get_all_triangle_indices(dm,False)
 if triangle_gaps:raise RuntimeError('Expected compact native triangle IDs')
 old_triangles=len(u.GeometryScript_List.convert_triangle_list_to_array(old_indices))
 Ed.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(**kwargs),0,True)
 if Q.get_vertex_count(dm)!=start+len(verts):raise RuntimeError('Patch append vertex count mismatch')
 for i,ws in enumerate(weights):B.set_vertex_bone_weights(dm,start+i,[u.GeometryScriptBoneWeight(bone_index=bone_ids[n],weight=w) for n,w in ws.items()])
 for i,mat in enumerate(materials):u.GeometryScript_Materials.set_triangle_material_id(dm,old_triangles+i,mat,True)
 for ti in sorted(remove):
  _,ok=Ed.delete_triangle_from_mesh(dm,ti,True)
  if not ok:raise RuntimeError('Cannot remove damaged palm triangle')
 backup=R/'Before'/file.relative_to(P);backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():shutil.copy2(file,backup)
 original_slots=[s.copy() for s in asset.materials];lod_count=S.get_lod_count(asset)
 options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=False,enable_recompute_normals=False,enable_recompute_tangents=True,
   bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write native palm patch '+path)
 # Only regenerate the mesh's existing LODs; do not alter outfit reduction settings.
 if lod_count>1 and not S.regenerate_lod(asset,lod_count,True,False):raise RuntimeError('Cannot rebuild existing LODs '+path)
 after=dynamic(asset)
 if bones_signature(after)!=before_bones:raise RuntimeError('Native reference changed; leave asset unsaved '+path)
 if [(str(s.material_slot_name),s.material_interface) for s in asset.materials]!=[(str(s.material_slot_name),s.material_interface) for s in original_slots]:raise RuntimeError('Material slots changed; leave unsaved '+path)
 E.set_metadata_tag(asset,'PalmSurfaceRepair20261014','Concave perimeter triangulation; local inherited palm holes repaired; native bind and materials preserved')
 if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Cannot save '+path)
 imp=asset.get_editor_property('asset_import_data');source=imp.get_first_filename() if imp else ''
 row=dict(path=path,patches=len(entry['patches']),removed_triangles=len(remove),added_triangles=len(faces),lods=lod_count,
   reference_bones_unchanged=True,material_slots_unchanged=True,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),import_source=source,runtime_tested=False)
 receipt.write_text(json.dumps(row,indent=2));print('PALM_REPAIR_SAVED',path,row['patches'],'LODS',lod_count,flush=True)
print('PALM_REPAIR_INSTALL_COMPLETE',len(plans),flush=True)
