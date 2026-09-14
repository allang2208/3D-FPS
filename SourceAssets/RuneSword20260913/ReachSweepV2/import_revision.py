"""Install the material fix and six ReachSweepV2 clips at the equipped item paths."""
import json
import shutil
from pathlib import Path
import unreal as u

P = Path(__file__).parent
D = '/Game/Weapons/AzureRunesword20260913'
content = P.parents[2] / 'Content/Weapons/AzureRunesword20260913'
backup = P / 'Before'
backup.mkdir(exist_ok=True)
names = ['M_AzureRunesword', 'SK_AzureRunesword_Manny_Skeleton']
clips = ['Idle', 'Walk', 'Slash1', 'Slash2', 'Equip', 'Sprint']
names += ['A_RuneSword_' + name for name in clips]
for name in names:
    file = content / (name + '.uasset')
    target = backup / file.name
    if not target.exists():
        shutil.copy2(file, target)

mat = u.load_asset(D + '/M_AzureRunesword')
# The original null-RHI import never triggered the editor's automatic usage
# detection. Enable the skeletal vertex-factory permutation explicitly.
mat.set_editor_property('used_with_skeletal_mesh', True)
u.MaterialEditingLibrary.recompile_material(mat)
u.EditorAssetLibrary.save_loaded_asset(mat)
receipt = {'material': mat.get_path_name(), 'used_with_skeletal_mesh': True, 'animations': []}

u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
sk = u.load_asset(D + '/SK_AzureRunesword_Manny')
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
tools = u.AssetToolsHelpers.get_asset_tools()
for name in clips:
    opt = u.FbxImportUI()
    opt.automated_import_should_detect_type = False
    opt.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh = False
    opt.import_animations = True
    opt.import_materials = False
    opt.import_textures = False
    opt.skeleton = sk.skeleton
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
    opt.anim_sequence_import_data.set_editor_property('custom_sample_rate', 120)
    task = u.AssetImportTask()
    task.filename = str(P / ('Export/A_RuneSword_' + name + '.fbx'))
    task.destination_path = D
    task.destination_name = 'A_RuneSword_' + name
    task.automated = True
    task.replace_existing = True
    task.save = True
    task.options = opt
    tools.import_asset_tasks([task])
    seq = u.load_asset(D + '/A_RuneSword_' + name)
    if not task.imported_object_paths or not seq:
        raise RuntimeError('Animation import did not complete: ' + name)
    if compression:
        seq.set_editor_property('bone_compression_settings', compression)
    u.EditorAssetLibrary.save_loaded_asset(seq)
    receipt['animations'].append({'source': task.filename, 'asset': seq.get_path_name()})
    u.log('RUNESWORD_V2_IMPORTED ' + name)

(P / 'import_receipt.json').write_text(json.dumps(receipt, indent=2))
u.log('RUNESWORD_V2_IMPORT_COMPLETE')
