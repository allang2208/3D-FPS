import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923/UVRepair');C=O.parent;R=C.parents[1];BASE='/Game/Weapons/SVDDragunov20260922';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Stop the active play session before replacing the SVD mesh')
if JOB=='skeletal':jobs=[(BASE+'/Complete20260923/SK_SVD_Manny',C/'Exports/SK_SVD_Manny.fbx',True)]
else:
 names=['Body','Magazine','Trigger','ChargingHandle','SafetyLever','ScopeBody','ScopeMount','ScopeLens'];start=int(JOB[-1])*4
 jobs=[(BASE+'/Meshes/SM_SVD_'+key,C.parent/'SVDDragunov20260922/Authored'/('SM_SVD_'+key+'.fbx'),False) for key in names[start:start+4]]
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for path,file,skel in jobs:
 if path in dirty:raise RuntimeError('Unsaved SVD asset: '+path)
 if not E.does_asset_exist(path):raise RuntimeError('Missing current SVD asset: '+path)
 p=R/'Content'/Path(path.removeprefix('/Game/')).with_suffix('.uasset');backup=O/'Before/Content'/Path(path.removeprefix('/Game/')).with_suffix('.uasset');backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():shutil.copy2(p,backup)
receipt_path=O/'import_fixed.json';receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for path,file,skel in jobs:
  mesh=u.load_asset(path);slots=list(mesh.materials if skel else mesh.static_materials);mapping={str(x.material_slot_name):x.material_interface for x in slots}
  opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.import_mesh=True;opts.import_as_skeletal=skel;opts.import_animations=False;opts.import_materials=False;opts.import_textures=False
  opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skel else u.FBXImportType.FBXIT_STATIC_MESH
  if skel:opts.skeleton=mesh.skeleton;opts.create_physics_asset=False
  else:opts.static_mesh_import_data.set_editor_property('generate_lightmap_u_vs',False)
  t=u.AssetImportTask();t.filename=str(file);t.destination_path=path.rsplit('/',1)[0];t.destination_name=path.rsplit('/',1)[1];t.options=opts;t.factory=u.FbxFactory();t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);mesh=u.load_asset(path)
  current=list(mesh.materials if skel else mesh.static_materials)
  for slot in current:
   name=str(slot.material_slot_name)
   if name not in mapping:raise RuntimeError('Material-slot identity changed: '+name)
   slot.material_interface=mapping[name]
  if skel:mesh.materials=current
  else:mesh.static_materials=current
  if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save failed: '+path)
  receipt[path]={'saved':True,'source':str(file),'source_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'material_slots':{str(x.material_slot_name):x.material_interface.get_path_name() for x in current},'uv':'UV0.v corrected for original 4K atlas; arms unmodified'}
  receipt_path.write_text(json.dumps(receipt,indent=2));print('SVD_UV_ASSET_SAVED',path)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
