import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;R=O.parent;P='/Game/Weapons/PKMLowpoly20260922';A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary
mesh=u.load_asset(P+'/SK_PKM_Manny');skeleton=mesh.skeleton
if not skeleton.get_path_name().startswith(P+'/'):raise RuntimeError('PKM must use its private skeleton')
bindings={str(s.material_slot_name):s.material_interface for s in mesh.materials}
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=skeleton
opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
opt.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',True)
t=u.AssetImportTask();t.filename=str(R/'Integration04/Exports/SK_PKM_Manny.fbx');t.destination_path=P;t.destination_name='SK_PKM_Manny';t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.options=opt;t.factory=u.FbxFactory();t.save=False
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
try:
 u.SystemLibrary.execute_console_command(None,flag+' 0');A.import_asset_tasks([t])
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
if not t.imported_object_paths:raise RuntimeError('FBX task did not return an imported PKM asset')
mesh=u.load_asset(P+'/SK_PKM_Manny');slots=mesh.materials
for i,s in enumerate(slots):s.material_interface=bindings[str(s.material_slot_name)];slots[i]=s
mesh.set_editor_property('materials',slots)
for asset in [mesh,mesh.skeleton]:
 if not L.save_loaded_asset(asset,False):raise RuntimeError('PKM rest-pose save failed: '+asset.get_path_name())
(O/'mesh_reimport.json').write_text(json.dumps({'mesh':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'updated_skeleton_reference_pose':True,'saved':True},indent=2))
print('PKM rest-pose mesh and skeleton saved.')
