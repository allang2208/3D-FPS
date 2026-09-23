"""Install the refined magazine in the active modular SVD, with stable slots."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;project=Path(u.Paths.project_dir()).resolve()
path='/Game/Weapons/SVDDragunov20260922/Accessories20260923/SK_SVD_Modular'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Active PIE: no mesh import')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if path in dirty:raise RuntimeError('Unsaved target mesh')
mesh=u.load_asset(path);sk=mesh.skeleton;physics=mesh.physics_asset;post=mesh.get_editor_property('post_process_anim_blueprint')
bindings={str(s.material_slot_name):s.material_interface for s in mesh.materials}
finish=json.loads((O/'finish_receipt.json').read_text())
for name,mat in bindings.items():
 row=finish['materials'].get(mat.get_path_name())
 if row:bindings[name]=u.load_asset(row['dry'])
# Rim, follower and floorplate share the new magazine atlas, not the generic
# installation steel's unrelated UV projection. Retain the existing slot name.
bindings['SVD_InterfaceSteel']=bindings['SM_SVD_Magazine_001']
f=project/'Content'/(path.removeprefix('/Game/')+'.uasset');dest=O/'Before'/f.relative_to(project/'Content')
if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
try:
 u.SystemLibrary.execute_console_command(None,flag+' 0')
 opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
 opts.import_as_skeletal=True;opts.import_mesh=True;opts.import_animations=False;opts.import_materials=False;opts.import_textures=False;opts.create_physics_asset=False;opts.skeleton=sk
 opts.set_editor_property('reset_to_fbx_on_material_conflict',True)
 d=opts.skeletal_mesh_import_data;d.set_editor_property('update_skeleton_reference_pose',False);d.set_editor_property('use_t0_as_ref_pose',False);d.set_editor_property('preserve_smoothing_groups',True);d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
 task=u.AssetImportTask();task.filename=str(O/'Exports/SK_SVD_Modular.fbx');task.destination_path=path.rsplit('/',1)[0];task.destination_name=path.rsplit('/',1)[1]
 task.options=opts;task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
 if not task.imported_object_paths:raise RuntimeError('SVD mesh import failed')
 mesh=u.load_asset(path);slots=mesh.materials
 for i,s in enumerate(slots):s.material_interface=bindings[str(s.material_slot_name)];slots[i]=s
 mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',physics);mesh.set_editor_property('post_process_anim_blueprint',post)
 if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('SVD mesh save failed')
 report={'asset':mesh.get_path_name(),'saved':True,'source':task.filename,'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.materials},'animations_changed':False,'game_tested':False}
 (O/'model_import_receipt.json').write_text(json.dumps(report,indent=2))
 print('SVD_MATTE_MODEL_IMPORTED_SAVED',mesh.get_path_name(),flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
