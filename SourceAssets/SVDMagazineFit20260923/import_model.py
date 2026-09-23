"""Replace only the active SVD modular mesh, retaining its current live settings."""
import unreal as u,json,shutil,hashlib
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDMagazineFit20260923');PROJECT=O.parents[1]
path='/Game/Weapons/SVDDragunov20260922/Accessories20260923/SK_SVD_Modular'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Active play session: preserve state; no mesh import')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if path in dirty:raise RuntimeError('Unsaved target mesh: '+path)
old=u.load_asset(path)
if not old:raise RuntimeError('Missing active modular SVD mesh')
bindings={str(s.material_slot_name):s.material_interface for s in old.materials}
bindings['SVD_InterfaceSteel']=u.load_asset('/Game/Weapons/SVDDragunov20260922/Accessories20260923/Materials/M_SVD_InterfaceSteel')
if not bindings['SVD_InterfaceSteel']:raise RuntimeError('Missing existing SVD steel material')
sk=old.get_editor_property('skeleton');physics=old.get_editor_property('physics_asset')
post=old.get_editor_property('post_process_anim_blueprint')
disk=PROJECT/'Content'/Path(path.removeprefix('/Game/')).with_suffix('.uasset');backup=O/'Before'/Path(path.removeprefix('/Game/')).with_suffix('.uasset');backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():shutil.copy2(disk,backup)
source=O/'Exports/SK_SVD_Modular.fbx'
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opts.import_as_skeletal=True
 opts.import_mesh=True;opts.import_animations=False;opts.import_materials=False;opts.import_textures=False;opts.create_physics_asset=False;opts.skeleton=sk;opts.set_editor_property('reset_to_fbx_on_material_conflict',True)
 d=opts.skeletal_mesh_import_data;d.set_editor_property('update_skeleton_reference_pose',False);d.set_editor_property('use_t0_as_ref_pose',False);d.set_editor_property('preserve_smoothing_groups',True);d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
 t=u.AssetImportTask();t.filename=str(source);t.destination_path=path.rsplit('/',1)[0];t.destination_name=path.rsplit('/',1)[1];t.options=opts;t.factory=u.FbxFactory();t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
 if not t.imported_object_paths:raise RuntimeError('SVD magazine mesh import failed')
 mesh=u.load_asset(path);slots=mesh.materials
 for i,slot in enumerate(slots):slot.material_interface=bindings[str(slot.material_slot_name)];slots[i]=slot
 mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',physics);mesh.set_editor_property('post_process_anim_blueprint',post)
 if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('SVD mesh save failed')
 (O/'model_import_receipt.json').write_text(json.dumps({'asset':mesh.get_path_name(),'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
  'saved':True,'before':str(backup),'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots},'game_tested':False},indent=2))
 print('SVD_MAG_MODEL_IMPORTED_SAVED',mesh.get_path_name(),flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
