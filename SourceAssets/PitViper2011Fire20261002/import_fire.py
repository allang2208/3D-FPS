"""Replace and save eight fire animations on the existing native skeletons."""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

job = Path(__file__).parent
project = job.parents[1]
canonical = job.parent / 'PitViper2011Integration20261002'
destination = '/Game/Weapons/PitViper2011/Integrated20261002'
library = u.EditorAssetLibrary
asset_tools = u.AssetToolsHelpers.get_asset_tools()
receipt = dict(status='producing', saved=[], animations={}, runtime_tested=False,
               acceptance_rendered=False)

def record():
    (job / 'import_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf8')

def load(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing production dependency: ' + path)
    return asset

# Preserve loaded, unsaved work in the existing editor instead of overwriting it.
headless = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
editor = None if headless else u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('An active game world occupies these animations. Existing PIE retained.')
targets = []
for side, relative in [('single', 'Single'), ('r', 'Dual/r'), ('l', 'Dual/l')]:
    auth = json.loads((job / relative / 'authoring.json').read_text(encoding='utf8'))
    mesh = load(destination + '/' + relative + '/' + Path(auth['mesh']).stem)
    for kind, clip in auth['clips'].items():
        file = canonical / relative / clip['file']
        path = destination + '/' + relative + '/Animations/' + file.stem
        targets.append((side, relative, kind, clip, file, path, mesh.skeleton))
dirty = set() if headless else {package.get_name() for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
occupied = [path for *_, path, skeleton in targets if path in dirty]
if occupied:
    raise RuntimeError('Unsaved fire animation edits retained: ' + ', '.join(occupied))
compression = load('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
flag = 'Interchange.FeatureFlags.Import.FBX'
previous_flag = u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None, flag + ' 0')
record()
try:
    for side, relative, kind, clip, file, path, skeleton in targets:
        package_file = project / 'Content' / (path.removeprefix('/Game/') + '.uasset')
        backup = job / 'BeforeAssets' / (path.removeprefix('/Game/') + '.uasset')
        if package_file.exists() and not backup.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(package_file, backup)
        signature = hashlib.sha256(file.read_bytes()).hexdigest()
        asset = load(path)
        if library.get_metadata_tag(asset, 'PitViperSourceSHA256') != signature:
            options = u.FbxImportUI()
            options.automated_import_should_detect_type = False
            options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
            options.import_mesh = False
            options.import_animations = True
            options.skeleton = skeleton
            options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
            options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 120)
            task = u.AssetImportTask()
            task.filename = str(file)
            task.destination_path = destination + '/' + relative + '/Animations'
            task.destination_name = file.stem
            task.automated = True
            task.replace_existing = True
            task.replace_existing_settings = True
            task.save = False
            task.options = options
            task.factory = u.FbxFactory()
            asset_tools.import_asset_tasks([task])
            asset = load(path)
        asset.set_editor_property('bone_compression_settings', compression)
        library.set_metadata_tag(asset, 'PitViperSourceSHA256', signature)
        library.set_metadata_tag(asset, 'PitViperFireRecipe', json.dumps(clip['fire_motion']))
        library.set_metadata_tag(asset, 'SourceAttribution',
            'Low Poly TTI JW4 Pit Viper 2011 by D_U; Sketchfab 2daaf7fe78604ee7941a4ad5fd4d0153; CC BY 4.0; '
            'modified: rig, native V7 arms, M1911-based fire animation, materials.')
        if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
            raise RuntimeError('Save failed: ' + path)
        receipt['saved'].append(asset.get_path_name())
        receipt['animations'][side + '/' + kind] = dict(asset=asset.get_path_name(),
            duration=asset.get_play_length(), source_sha256=signature, fire_motion=clip['fire_motion'])
        record()
finally:
    u.SystemLibrary.execute_console_command(None, flag + ' ' + str(previous_flag))

# Merge replaced rows into the existing delivery, retaining its other 51 clips.
original_path = canonical / 'import_receipt.json'
original_text = original_path.read_text(encoding='utf8')
original = json.loads(original_text)
original['animations'].update(receipt['animations'])
original['fire_upgrade'] = dict(producer=str(job), saved_animation_count=len(receipt['saved']), runtime_tested=False)
if original_path.read_text(encoding='utf8') != original_text:
    raise RuntimeError('Original import receipt changed during publication')
original_path.write_text(json.dumps(original, ensure_ascii=False, indent=2), encoding='utf8')
receipt['status'] = 'imported_and_saved'
record()
print('PIT_VIPER_FIRE_ANIMATIONS_IMPORTED_AND_SAVED', len(receipt['saved']))
