"""Import the corrected binding; retain normal MikkTSpace tangent generation."""
from pathlib import Path
import json,unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/AlchemyManualBindingTangents20261016')
HOST=ROOT.parent/'PotionWorkbenchDesign20261015/IntegrationV1/UEImportHost'
if Path(u.Paths.project_dir()).resolve()!=HOST.resolve():raise RuntimeError('Use the isolated manual import host')
DEST='/Game/Building/PotionWorkbench20261015/ManualV10/Meshes'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
report=dict(complete=False,saved=[],runtime_tested=False)
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False
    data.convert_scene=True;data.convert_scene_unit=True;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=u.AssetImportTask();task.filename=str(ROOT/'Export/SM_AlchemyManualBinding.fbx')
    task.destination_path=DEST;task.destination_name='SM_AlchemyManualBinding'
    task.automated=True;task.replace_existing=True;task.save=False;task.options=opt
    A.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/SM_AlchemyManualBinding')
    if not mesh:raise RuntimeError('Binding import failed')
    old=u.load_asset('/Game/Building/PotionWorkbench20261015/ManualV9/Meshes/SM_AlchemyManualBinding')
    materials={str(slot.material_slot_name):slot.material_interface for slot in old.static_materials}
    for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,materials[str(slot.material_slot_name)])
    u.load_module('StaticMeshEditor');sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    settings=sm.get_lod_build_settings(mesh,0)
    settings.use_full_precision_u_vs=True;settings.generate_lightmap_u_vs=False
    settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True
    sm.set_lod_build_settings(mesh,0,settings)
    E.set_metadata_tag(mesh,'SourceAuthor','evildeer');E.set_metadata_tag(mesh,'SourceLicense','CC BY 4.0')
    E.set_metadata_tag(mesh,'BindingUVRepair','Authored brass and spine detail UVs transferred from UV贴图 to UVMap')
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Binding save failed')
    report.update(complete=True,saved=[mesh.get_path_name()],mikk_t_space=True,recompute_tangents=True)
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
    (ROOT/'import-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('BOOK_BINDING_TANGENTS_SAVED')
