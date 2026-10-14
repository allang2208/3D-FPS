"""Import and save the requested solid connectors, without a preview/test run."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;PROJECT=Path(u.Paths.project_dir()).resolve();ROOT='/Game/Weapons/LMG201/GripSolidJunction20261007'
model=json.loads((O/'model.json').read_text());E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils;M=u.GeometryScript_Materials
RP=O/'install_receipt.json';R=json.loads(RP.read_text()) if RP.exists() else {'complete':False,'meshes':{},'runtime_tested':False,'rendered':False}
def record():RP.write_text(json.dumps(R,indent=2))
def disk(p):return PROJECT/'Content'/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(p):return hashlib.sha256(disk(p).read_bytes()).hexdigest()
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def outcome(result):
 if isinstance(result,tuple) and any(isinstance(v,u.GeometryScriptOutcomePins) and v!=u.GeometryScriptOutcomePins.SUCCESS for v in result):raise RuntimeError('Mesh transfer failed')
dirty=set()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
 sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
 if sub and sub.get_game_world():raise RuntimeError('PIE active; preserve current session')
 dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for key,row in model['meshes'].items():
 if row['path'] in dirty:raise RuntimeError('Unsaved target '+key)
 expected=R['meshes'].get(key,{}).get('sha256',row['source_sha256'])
 if sha(row['path'])!=expected:raise RuntimeError('Concurrent target changed '+key)
for key,row in model['meshes'].items():
 if key in R['meshes']:continue
 mesh=load(row['path']);slots=[s.copy() for s in mesh.static_materials]
 before=O/'Before'/disk(row['path']).relative_to(PROJECT/'Content');before.parent.mkdir(parents=True,exist_ok=True)
 if not before.exists():shutil.copy2(disk(row['path']),before)
 digest=hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest();candidate_path=ROOT+'/Sources/SM_Solid_'+key+'_'+digest[:10]
 candidate=u.load_asset(candidate_path)
 if not candidate:
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
  data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.remove_degenerates=True;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path=ROOT+'/Sources';task.destination_name=candidate_path.rsplit('/',1)[1];task.factory=u.FbxFactory();task.options=opt;task.automated=True;task.save=False
  flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
  try:A.import_asset_tasks([task])
  finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
  candidate=load(candidate_path)
 dm=u.DynamicMesh();outcome(G.copy_mesh_from_static_mesh(candidate,dm,u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=0)))
 # Current 201 grips use one continuous finish; retain the empty interface slot.
 for i in range(len(candidate.static_materials)):M.remap_material_i_ds(dm,i,1000+i)
 for i in range(len(candidate.static_materials)):M.remap_material_i_ds(dm,1000+i,1)
 opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],enable_recompute_normals=False,enable_recompute_tangents=True,enable_remove_degenerates=True)
 for target in (candidate,mesh):
  outcome(G.copy_mesh_to_static_mesh(dm,target,opts,u.GeometryScriptMeshWriteLOD(lod_index=0)));target.static_materials=[s.copy() for s in slots]
  E.set_metadata_tag(target,'GripJunctionVersion','SolidIntegrated-20261007');E.set_metadata_tag(target,'GripJunctionAuthor','SourceAssets/LMG201GripSolidJunction20261007/README.md')
  target.get_editor_property('asset_import_data').scripted_add_filename(row['fbx'],0,'Solid integrated 201 grip junction');save(target)
 R['meshes'][key]={'path':row['path'],'sha256':sha(row['path']),'source_sha256':row['source_sha256'],'fbx':row['fbx'],'blend':row['blend'],'fbx_sha256':digest,'candidate':candidate_path,'saved':True,
  'materials':[s.material_interface.get_path_name() if s.material_interface else None for s in slots],'material_changed':False,'cut_z_m':model['operations'][key]['cut_z_m']};record();print('SOLID_JUNCTION_SAVED',key,flush=True)
R['complete']=len(R['meshes'])==len(model['meshes'])
if R['complete']:R.pop('pending_reason',None)
record();print('SOLID_JUNCTION_COMPLETE',R['complete'],flush=True)
