"""Import the continuous clip and update only the dedicated treasure config."""
import json
from pathlib import Path
import unreal as u

HERE = Path(__file__).parent
PROJECT = HERE.parents[1]
ROOT = '/Game/Props/GamedevTreasureChest20260922'
NAME = 'A_TreasureChest_Opening'
UE = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if UE.get_game_world():
    raise RuntimeError('Animation import needs editor mode; preserve the running game.')
world = UE.get_editor_world()
flag = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(flag)
asset = u.load_asset(ROOT+'/'+NAME)
if not asset:
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_materials = False
    options.import_textures = False
    options.create_physics_asset = False
    options.import_as_skeletal = True
    options.import_mesh = False
    options.import_animations = True
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.skeleton = u.load_asset(ROOT+'/SK_GamedevTreasureChest_Skeleton')
    if not options.skeleton:
        raise RuntimeError('Migrated treasure skeleton unavailable')
    data = options.anim_sequence_import_data
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    task = u.AssetImportTask()
    task.filename = str(HERE/'Authored'/(NAME+'.fbx'))
    task.destination_path = ROOT
    task.destination_name = NAME
    task.automated = True
    task.save = False
    task.replace_existing = False
    task.set_editor_property('async_',False)
    task.options = options
    task.factory = u.FbxFactory()
    try:
        u.SystemLibrary.execute_console_command(world,flag+' 0')
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        objects = task.get_objects()
        asset = next((a for a in objects if a.get_path_name()==ROOT+'/'+NAME+'.'+NAME),None)
        if not asset:
            raise RuntimeError('Opening import did not produce the requested asset')
    finally:
        u.SystemLibrary.execute_console_command(world,flag+' '+str(previous))
if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(ROOT+'/'+NAME)],False):
    raise RuntimeError('Opening asset save failed')
config_path = PROJECT/'Content/ColdSteelData/treasure_chest_assets.json'
config = json.loads(config_path.read_text(encoding='utf-8-sig'))
config['opening'] = asset.get_path_name()
for path in (config_path,HERE/'treasure_assets.json'):
    path.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
receipt = dict(asset=asset.get_path_name(),saved=True,config=str(config_path),tested=False)
(HERE/'opening_import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('TREASURE_OPENING_SAVED '+json.dumps(receipt))
