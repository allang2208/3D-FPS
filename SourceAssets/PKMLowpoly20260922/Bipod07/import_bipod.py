import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/PKMLowpoly20260922/Bipod07';A=u.AssetToolsHelpers.get_asset_tools()
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
t=u.AssetImportTask();t.filename=str(O/'Exports/SM_PKM_Bipod.fbx');t.destination_path=P;t.destination_name='SM_PKM_Bipod';t.options=opt;t.factory=u.FbxFactory();t.automated=True;t.replace_existing=True;t.save=False
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
try:
 u.SystemLibrary.execute_console_command(None,flag+' 0');A.import_asset_tasks([t])
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
mesh=u.load_asset(P+'/SM_PKM_Bipod')
if not mesh:raise RuntimeError('Bipod import did not produce an asset')
mat=u.load_asset(P+'/Materials/M_PKM_QBZ_Body')
for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,mat)
if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Bipod save failed')
(O/'bipod_import.json').write_text(json.dumps({'asset':mesh.get_path_name(),'mount':'WPN_root; inverse component bind transform','saved':True},indent=2))
print('PKM07: separated bipod saved.')
