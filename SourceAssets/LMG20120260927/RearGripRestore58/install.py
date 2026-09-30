"""Publish only the three restored 201 rear grips, preserving live bindings."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;PROJECT=O.parents[2];P='/Game/Weapons/LMG201/RearGripRestore58'
cap=json.loads((O/'capture.json').read_text());model=json.loads((O/'model.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils;M=u.GeometryScript_Materials
receipt=json.loads((O/'delivery.json').read_text()) if (O/'delivery.json').exists() else {'status':'installing','backups':{},'saved':{},'runtime_tested':False,'rendered':False}
def record():(O/'delivery.json').write_text(json.dumps(receipt,indent=2))
receipt['status']='installing';record()
def file(p):return PROJECT/'Content'/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(p):return hashlib.sha256(file(p).read_bytes()).hexdigest()
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if sub and sub.get_game_world():raise RuntimeError('PIE active; assets retained')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for key in ['Body','stable','balanced','phantom']:
 row=cap[key];p=row['asset'];expected=receipt['saved'].get(p,{}).get('sha256',row['sha256'])
 if p in dirty or sha(p)!=expected:raise RuntimeError('Concurrent target retained '+p)
bindings={};sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for key in ['stable','balanced','phantom']:
 row=model['meshes'][key];path=cap[key]['asset'];a=load(path);slots=[s.copy() for s in a.static_materials]
 if len(slots)!=2:raise RuntimeError('Rear grip slot contract changed '+key)
 bindings[path]={str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in slots}
 digest=hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest()
 if receipt['saved'].get(path,{}).get('source_sha256')==digest and receipt['saved'][path].get('remove_degenerate_build_faces'):continue
 candidate_path=P+'/Parts/SM_R58_'+key+'_'+digest[:10];candidate=u.load_asset(candidate_path)
 if not candidate:
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
  data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.remove_degenerates=True;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path=P+'/Parts';task.destination_name=candidate_path.rsplit('/',1)[1];task.factory=u.FbxFactory();task.options=opt;task.automated=True;task.save=False
  flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
  try:A.import_asset_tasks([task])
  finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
  candidate=load(candidate_path)
 dm,status=G.copy_mesh_from_static_mesh(candidate,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read imported '+key)
 # The former separate collar slot stays in the table, with no geometry.
 for i in range(len(candidate.static_materials)):M.remap_material_i_ds(dm,i,1000+i)
 for i in range(len(candidate.static_materials)):M.remap_material_i_ds(dm,1000+i,1)
 def write_geometry(target):
  opt=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],enable_recompute_normals=False,enable_recompute_tangents=True)
  _,result=G.copy_mesh_to_static_mesh(dm,target,opt,u.GeometryScriptMeshWriteLOD())
  if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write '+key)
  target.static_materials=[s.copy() for s in slots]
  settings=sm.get_lod_build_settings(target,0);settings.remove_degenerates=True;settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_full_precision_u_vs=True;sm.set_lod_build_settings(target,0,settings)
 write_geometry(candidate);E.set_metadata_tag(candidate,'201RearGripRevision','RearGripRestore58 original textured topology, local receiver neck');save(candidate)
 if path not in receipt['backups']:
  dest=O/'Before'/file(path).relative_to(PROJECT/'Content');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file(path),dest);receipt['backups'][path]={'file':str(dest),'sha256':sha(path)};record()
 write_geometry(a);a.get_editor_property('asset_import_data').scripted_add_filename(row['fbx'],0,'RearGripRestore58 original restored grip and fitted neck');E.set_metadata_tag(a,'201RearGripRevision','RearGripRestore58');E.set_metadata_tag(a,'201DetailSource',row['blend']);save(a)
 receipt['saved'][path]={'sha256':sha(path),'source_sha256':digest,'candidate':candidate_path,'triangles':model['operations'][key]['triangles'],'slot_bindings':bindings[path],'pivot_changed':False,'remove_degenerate_build_faces':True};record();print('R58_LIVE_SAVED',key,flush=True)
manifest=O.parent/'Material21/bindings.json';data=json.loads(manifest.read_text());data['meshes'].update(bindings);data['current_reargrip_revision']='RearGripRestore58';manifest.write_text(json.dumps(data,indent=2));(O/'bindings.json').write_text(json.dumps(bindings,indent=2))
receipt.update(status='three_restored_reargrips_saved',body_modified=False,materials_modified=False,animations_modified=False,native_code_modified=False,wet_mapping_modified=False,runtime_tested=False,rendered=False);record();print('R58_PUBLICATION_COMPLETE',flush=True)
