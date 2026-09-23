"""Import the hinged flap while retaining current Finish20 material bindings."""
import unreal as u,json,sys
from pathlib import Path
O=Path(__file__).parent;R=O.parent
P='/Game/Weapons/PKMLowpoly20260922/Accessories14'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
# Current-editor callers must finish PIE before replacing its skeletal asset.
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
 editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
 if editor and editor.get_game_world():raise RuntimeError('Finish PIE before the PKM mesh import')
mesh=u.load_asset(P+'/SK_PKM_Manny_Modular');skeleton=mesh.skeleton
if not skeleton.get_path_name().startswith('/Game/Weapons/PKMLowpoly20260922/'):
 raise RuntimeError('PKM private skeleton required')
sys.path.insert(0,str(R/'Belt08'))
from material_binding import capture_bindings,bind_materials
bindings=capture_bindings(mesh)
(O/'materials_before.json').write_text(json.dumps({n:m.get_path_name() for n,m in bindings.items()},indent=2))
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False
opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=skeleton
d=opt.skeletal_mesh_import_data;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
d.set_editor_property('update_skeleton_reference_pose',False)
d.set_editor_property('use_t0_as_ref_pose',False);d.set_editor_property('preserve_smoothing_groups',True)
t=u.AssetImportTask();t.filename=str(O/'Exports/SK_PKM_Manny_Modular.fbx')
t.destination_path=P;t.destination_name='SK_PKM_Manny_Modular';t.options=opt;t.factory=u.FbxFactory()
t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
try:
 u.SystemLibrary.execute_console_command(None,flag+' 0');A.import_asset_tasks([t])
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
mesh=u.load_asset(P+'/SK_PKM_Manny_Modular')
if not mesh or not t.imported_object_paths:raise RuntimeError('PKM hinged outlet mesh import failed')
mapping=bind_materials(mesh,{},bindings)
E.set_metadata_tag(mesh,'PKMExitCover','Motion21; source parts 58 and 101; parent PKM_Cover; Finish20 bindings retained')
for asset in [mesh,mesh.skeleton]:
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
(O/'imported.json').write_text(json.dumps({'mesh':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),
 'materials':mapping,'saved':True,'animations_reimported':False},indent=2))
print('PKM21_HINGED_OUTLET_MESH_AND_SKELETON_SAVED',flush=True)
