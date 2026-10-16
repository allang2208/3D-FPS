import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/PotionWorkbenchDesign20261015/RefinementV4')
HOST=ROOT.parent/'IntegrationV1/UEImportHost'
if Path(u.Paths.project_dir()).resolve()!=HOST.resolve():raise RuntimeError('Use the isolated potion asset host')
DEST='/Game/Building/PotionWorkbench20261015/RefinementV4'
material=u.load_asset('/Game/Building/PotionWorkbench20261015/V1/Materials/M_PW_SurfaceAtlas')
if not material:raise RuntimeError('Original workbench surface atlas is missing')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.import_mesh=True;opt.import_as_skeletal=False
opt.import_materials=False;opt.import_textures=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
data.convert_scene=True;data.convert_scene_unit=True;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    task=u.AssetImportTask();task.filename=str(ROOT/'Export/SM_AlchemyToolRests.fbx');task.destination_name='SM_AlchemyToolRests'
    task.destination_path=DEST;task.automated=True;task.replace_existing=True;task.save=False;task.options=opt
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(DEST+'/SM_AlchemyToolRests')
    if not mesh:raise RuntimeError('Support import failed')
    for i in range(len(mesh.static_materials)):mesh.set_material(i,material)
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Support save failed')
    (ROOT/'import-receipt.json').write_text(json.dumps({'complete':True,'saved':[mesh.get_path_name()],'runtime_tested':False},indent=2),encoding='utf-8')
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
