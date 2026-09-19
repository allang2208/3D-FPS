"""Install the V43 charged-attack clips at the existing runtime paths."""
import json
import shutil
from pathlib import Path
import unreal as u

P = Path(__file__).parent
D = '/Game/Weapons/AzureRunesword20260913'
content = P.parents[2] / 'Content/Weapons/AzureRunesword20260913'
asset_tools = u.AssetToolsHelpers.get_asset_tools()
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
skeleton = u.load_asset(D + '/SK_AzureRunesword_Manny').skeleton
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
receipt = []
for clip in ('HeavyCharge', 'HeavyRelease', 'Slash1'):
    name = 'A_RuneSword_' + clip
    current = content / (name + '.uasset')
    prior = P / 'Before' / (name + '.uasset')
    if current.exists() and not prior.exists():
        prior.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(current, prior)
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh = False
    options.import_animations = True
    options.import_materials = False
    options.import_textures = False
    options.skeleton = skeleton
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 480)
    task = u.AssetImportTask()
    task.filename = str(P / 'Export' / (name + '.fbx'))
    task.destination_path = D
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    task.options = options
    asset_tools.import_asset_tasks([task])
    sequence = u.load_asset(D + '/' + name)
    if not task.imported_object_paths or not sequence:
        raise RuntimeError('Animation import failed: ' + name)
    if compression:
        sequence.set_editor_property('bone_compression_settings', compression)
    if not u.EditorAssetLibrary.save_loaded_asset(sequence):
        raise RuntimeError('Animation save failed: ' + name)
    receipt.append({'source': task.filename, 'asset': sequence.get_path_name(),
                    'length_seconds': sequence.get_play_length()})
(P / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('RUNESWORD_V43_IMPORT_COMPLETE')
