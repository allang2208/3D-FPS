"""Import/save the fitted wrap as a new asset, retaining the shipped material."""
import json,hashlib
from pathlib import Path
import unreal as u
P=Path(__file__).parent
DEST='/Game/Weapons/DarkBow20260925/GripContactV22'
NAME='SM_Bow_GripWrap_Fitted'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Finish play mode before importing/saving the fitted grip')
receipt=P/'import-receipt.json'
r=json.loads(receipt.read_text()) if receipt.exists() else {'saved':{},'sources':{},'gameplay_tested':False}
path=DEST+'/'+NAME
if any(x.get_name().startswith(DEST+'/') for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserving unsaved grip contact packages')
source=P/'Export'/(NAME+'.fbx');digest=hashlib.sha256(source.read_bytes()).hexdigest()
if r['sources'].get(NAME)!=digest or not E.does_asset_exist(path):
    if E.does_asset_exist(path) and NAME not in r['saved']:raise RuntimeError('Existing unowned asset '+path)
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_animations=False
    opt.import_materials=False;opt.import_textures=False;opt.static_mesh_import_data.combine_meshes=True
    opt.static_mesh_import_data.auto_generate_collision=False
    opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=DEST;task.destination_name=NAME
    task.automated=True;task.replace_existing=NAME in r['saved'];task.save=False;task.options=opt
    A.import_asset_tasks([task]);asset=u.load_asset(path)
    if not asset:raise RuntimeError('Grip import did not produce an asset')
    material=u.load_asset('/Game/Weapons/DarkBow20260925/WoodLongbow20260925/M_WoodLongbow_PBR')
    slots=list(asset.static_materials)
    for slot in slots:slot.material_interface=material
    asset.static_materials=slots
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Grip save failed')
    r['saved'][NAME]=asset.get_path_name();r['sources'][NAME]=digest
    receipt.write_text(json.dumps(r,indent=2),encoding='utf8')
print('BOW_GRIP_CONTACT_SAVED',json.dumps(r))
