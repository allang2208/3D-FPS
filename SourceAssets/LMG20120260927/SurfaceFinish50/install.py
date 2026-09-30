"""Compile private materials, merge only selected body sections, save actual assets."""
import unreal as u, json, hashlib, shutil
from pathlib import Path
O=Path(__file__).parent;PROJECT=O.parents[2];P='/Game/Weapons/LMG201/SurfaceFinish50'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
G=u.GeometryScript_AssetUtils;M=u.GeometryScript_Materials;IL=u.GeometryScript_List;Ed=u.GeometryScript_MeshEdits
model=json.loads((O/'model.json').read_text());cap=json.loads((O/'Inputs/assets.json').read_text());BODY=model['body']
receipt_path=O/'delivery.json'
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {'status':'installing','backups':{},'saved':{},'animations_modified':False,'skeleton_modified':False,'native_code_modified':False,'runtime_tested':False,'rendered_acceptance':False}
def record():receipt_path.write_text(json.dumps(receipt,indent=2))
def file(p):return PROJECT/'Content'/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(p):return hashlib.sha256(file(p).read_bytes()).hexdigest()
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save '+a.get_path_name())
def backup(p):
 if p not in receipt['backups']:
  dest=O/'Before'/file(p).relative_to(PROJECT/'Content');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file(p),dest)
  receipt['backups'][p]={'file':str(dest),'sha256':sha(p)};record()
def dynamic(a):
 dm,result=G.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+a.get_path_name())
 return dm

dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for p,r in cap['meshes'].items():
 if '/Cloth' in p:continue
 expected=receipt['saved'].get(p,{}).get('sha256',r['sha256'])
 if p in dirty or sha(p)!=expected:raise RuntimeError('Concurrent asset retained '+p)

# Keep material-module globals isolated from this import/save transaction.
exec(compile((O/'materials.py').read_text(),str(O/'materials.py'),'exec'),{'__file__':str(O/'materials.py'),'__name__':'__main__'})
mats=json.loads((O/'materials.json').read_text())
body=load(BODY);digest=hashlib.sha256(Path(model['fbx']).read_bytes()).hexdigest()
partpath=P+'/Parts/SK_LMG201_F50_'+digest[:8];part=u.load_asset(partpath)
if not part:
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
 opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=opt.import_materials=opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=body.skeleton
 data=opt.skeletal_mesh_import_data;data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False);data.set_editor_property('preserve_smoothing_groups',True)
 data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
 task=u.AssetImportTask();task.filename=model['fbx'];task.destination_path=P+'/Parts';task.destination_name=partpath.rsplit('/',1)[1];task.factory=u.FbxFactory();task.options=opt;task.automated=True;task.save=False
 flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
 try:A.import_asset_tasks([task])
 finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
 part=load(partpath)
partslots=[s.copy() for s in part.materials]
for s in partslots:
 name=str(s.material_slot_name)
 if name not in mats['new_slots']:raise RuntimeError('Unexpected candidate material slot '+name)
 s.material_interface=load(mats['new_slots'][name])
part.materials=partslots;save(part)
receipt['saved'][partpath]={'sha256':sha(partpath),'source_sha256':digest};record()

if receipt['saved'].get(BODY,{}).get('source_sha256')!=digest:
 native=dynamic(body);added=dynamic(part);slots=[s.copy() for s in body.materials]
 _,tl,_=u.GeometryScript_MeshQueries.get_all_triangle_indices(native,False);triangles=IL.convert_triangle_list_to_array(tl);remove=[];counts={}
 for ti in range(len(triangles)):
  mid,valid=M.get_triangle_material_id(native,ti)
  if valid and str(slots[mid].material_slot_name) in model['replace_slots']:
   remove.append(ti);name=str(slots[mid].material_slot_name);counts[name]=counts.get(name,0)+1
 if not remove:raise RuntimeError('Source sections missing; current body retained')
 Ed.delete_triangles_from_mesh(native,IL.convert_array_to_index_list(remove,u.GeometryScriptIndexType.TRIANGLE),True)
 u.GeometryScript_BoneWeights.copy_bones_from_mesh(native,added,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=True))
 names={str(s.material_slot_name):i for i,s in enumerate(slots)}
 for s in partslots:
  name=str(s.material_slot_name)
  if name not in names:names[name]=len(slots);slots.append(s.copy())
  else:slots[names[name]].material_interface=s.material_interface
 for i in range(len(partslots)):M.remap_material_i_ds(added,i,1000+i)
 for i,s in enumerate(partslots):M.remap_material_i_ds(added,1000+i,names[str(s.material_slot_name)])
 Ed.append_mesh(native,added,u.Transform(),True)
 for s in slots:
  name=str(s.material_slot_name);target=mats['new_slots'].get(name,mats['bindings'].get(BODY,{}).get(name))
  if target:s.material_interface=load(target)
 options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 backup(BODY)
 _,result=G.copy_mesh_to_skeletal_mesh(native,body,options,u.GeometryScriptMeshWriteLOD())
 if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write 201 body')
 body.materials=slots;E.set_metadata_tag(body,'201SurfaceFinishRevision','SurfaceFinish50: explicit receiver pocket triangulation; bounded foreend, magazine, stock and grip surface finish')
 E.set_metadata_tag(body,'201SurfaceFinishSource',str(O/'LMG201_SurfaceFinish50.blend'))
 save(body);receipt['saved'][BODY]={'sha256':sha(BODY),'source_sha256':digest,'removed_by_slot':counts,'material_finish':'SurfaceFinish50'};record();print('F50_BODY_SAVED',BODY,flush=True)

for p,binds in mats['bindings'].items():
 if p==BODY or not binds or receipt['saved'].get(p,{}).get('material_finish')=='SurfaceFinish50':continue
 a=load(p);prop='materials' if isinstance(a,u.SkeletalMesh) else 'static_materials';slots=[s.copy() for s in a.get_editor_property(prop)]
 for s in slots:
  target=binds.get(str(s.material_slot_name))
  if target:s.material_interface=load(target)
 backup(p);a.set_editor_property(prop,slots);E.set_metadata_tag(a,'201SurfaceFinishRevision','SurfaceFinish50: private matched coating family');save(a)
 receipt['saved'][p]={'sha256':sha(p),'material_finish':'SurfaceFinish50','geometry_modified':False};record()

wetpath='/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials'
wet=load(wetpath);wetmap=dict(wet.get_editor_property('wet_materials'))
for job in mats['jobs'].values():wetmap[job['asset']]=load(job['asset'])
backup(wetpath);wet.set_editor_property('wet_materials',wetmap);save(wet)
receipt['saved'][wetpath]={'sha256':sha(wetpath),'material_finish':'SurfaceFinish50'};record()

bindings={}
for p in mats['bindings']:
 a=load(p);slots=a.materials if isinstance(a,u.SkeletalMesh) else a.static_materials
 bindings[a.get_path_name()]={str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in slots}
(O/'bindings.json').write_text(json.dumps(bindings,indent=2))
manifest=O.parent/'Material21/bindings.json';mapping=json.loads(manifest.read_text());mapping['meshes'].update(bindings)
mapping['current_geometry_revision']='SurfaceFinish50';mapping['current_material_revision']='SurfaceFinish50';manifest.write_text(json.dumps(mapping,indent=2))
receipt.update(status='current_surface_finish50_saved',material_count=len(mats['jobs']),source=str(O/'LMG201_SurfaceFinish50.blend'),cloth_reload_assets_modified=False,icon_pending=True)
record();print('F50_CURRENT_ASSETS_SAVED',len(receipt['saved']),flush=True)
