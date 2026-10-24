"""Produce the selected female MetaHuman's meshes in the authoring host."""
import json
import traceback
from pathlib import Path
import unreal as u

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')
ASSET = '/Game/EditableCharacters/Kaitlin/MHC_Kaitlin.MHC_Kaitlin'
OUTPUT = '/Game/Characters/KaitlinPlayer20261023/Native'
receipt = {'source': ASSET, 'output': OUTPUT, 'status': 'loading', 'saved_assets': []}

def save_receipt():
    (WORK / 'assembly_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('KAITLIN_ASSEMBLY ' + json.dumps(receipt), flush=True)

subsystem = None
character = None
try:
    # PostLoad discards missing wardrobe selections. Require the actual source
    # dependencies before loading/saving the preset so its selected hair survives.
    optional = Path(u.Paths.convert_relative_path_to_full(u.Paths.engine_plugins_dir())) / 'MetaHuman/MetaHumanCharacter/Content/Optional'
    dependencies = [
        optional / 'Grooms/Bindings/Hair/WI_Hair_L_Straight.uasset',
        optional / 'Grooms/Bindings/Eyebrows/WI_Eyebrows_L_Shaded.uasset',
        optional / 'Grooms/Bindings/Eyelashes/WI_Eyelashes_L_ThickCurl.uasset',
        optional / 'Clothing/WI_DefaultGarment.uasset',
    ]
    missing = [str(path) for path in dependencies if not path.is_file()]
    if missing:
        receipt['missing_core_data_dependencies'] = missing
        raise RuntimeError('Install UE 5.8 MetaHuman Creator Core Data before assembling Kaitlin; preserve the original wardrobe selections.')
    u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/Game/EditableCharacters/Kaitlin'], True)
    character = u.load_asset(ASSET)
    if not character:
        raise RuntimeError('The staged Kaitlin MetaHuman preset could not be loaded.')
    receipt['source_class'] = character.get_class().get_name()
    receipt['has_high_resolution_textures'] = bool(character.get_editor_property('has_high_resolution_textures'))
    save_receipt()
    subsystem = u.get_editor_subsystem(u.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError('MetaHuman could not initialize Kaitlin for assembly. See assembly log.')
    if not subsystem.can_build_meta_human(character, True):
        receipt['status'] = 'requesting_required_rig'
        save_receipt()
        rig = u.MetaHumanCharacterAutoRiggingRequestParams()
        rig.blocking = True
        rig.report_progress = False
        rig.rig_type = u.MetaHumanRigType.JOINTS_AND_BLEND_SHAPES
        subsystem.request_auto_rigging(character, rig)
        if not character.get_editor_property('has_high_resolution_textures'):
            receipt['status'] = 'requesting_required_texture_sources'
            save_receipt()
            textures = u.MetaHumanCharacterTextureRequestParams()
            textures.blocking = True
            textures.report_progress = False
            subsystem.request_texture_sources(character, textures)
    if not subsystem.can_build_meta_human(character, True):
        raise RuntimeError('Kaitlin still requires MetaHuman rig/texture prerequisites; see log for the specific reason.')
    if not u.EditorAssetLibrary.save_loaded_asset(character, False):
        raise RuntimeError('Unable to save the prepared Kaitlin character.')
    receipt['status'] = 'assembling'
    save_receipt()
    params = u.MetaHumanCharacterEditorBuildParameters()
    params.pipeline_type = u.MetaHumanDefaultPipelineType.OPTIMIZED
    params.pipeline_quality = u.MetaHumanQualityLevel.HIGH
    params.absolute_build_path = OUTPUT
    params.common_folder_path = OUTPUT + '/Common'
    params.name_override = 'Kaitlin'
    params.enable_wardrobe_item_validation = False
    try:
        subsystem.build_meta_human(character=character, params=params)
    except RuntimeError as error:
        # UE 5.8's bundled face rigs report duplicate reroute-link removals
        # during their automatic graph upgrade, even after assembly completes.
        # Retain that diagnostic and compile the produced rigs before saving.
        messages = str(error).splitlines()
        expected_rigs = ('CR_MetaHuman_HeadMovement_IK_Proc', 'Face_ControlBoard_CtrlRig')
        if not messages or any('Cannot break link' not in line or
                               not any(name in line for name in expected_rigs) for line in messages):
            raise
        receipt['control_rig_upgrade_messages'] = messages
    paths = u.EditorAssetLibrary.list_assets(OUTPUT, recursive=True, include_folder=False)
    meshes = []
    assets = []
    for path in paths:
        data = u.EditorAssetLibrary.find_asset_data(path)
        if str(data.asset_class_path.asset_name) == 'SkeletalMesh':
            meshes.append(path)
        asset = data.get_asset()
        if isinstance(asset, u.Blueprint):
            if isinstance(asset, u.ControlRigBlueprint):
                asset.recompile_vm()
            u.BlueprintEditorLibrary.compile_blueprint(asset)
            if 'ERROR' in str(asset.get_editor_property('status')):
                raise RuntimeError('Produced Blueprint did not compile: ' + path)
        assets.append(asset)
    if not meshes:
        raise RuntimeError('MetaHuman assembly did not produce skeletal mesh assets.')
    receipt['status'] = 'saving_assembled_packages'
    save_receipt()
    for asset in assets:
        if not u.EditorAssetLibrary.save_loaded_asset(asset, False):
            raise RuntimeError('Failed to save assembled asset: ' + asset.get_path_name())
        receipt['saved_assets'].append(asset.get_path_name())
        (WORK / 'assembly_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    receipt['skeletal_meshes'] = meshes
    receipt['status'] = 'native_assembly_saved_in_authoring_host'
    receipt['runtime_published'] = False
except Exception:
    receipt['status'] = 'assembly_incomplete'
    receipt['error'] = traceback.format_exc()
    raise
finally:
    save_receipt()
    if subsystem and character and subsystem.is_object_added_for_editing(character):
        subsystem.remove_object_to_edit(character)
