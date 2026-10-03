"""Import the eight ASH-12 grip-family camera-guard clips at their runtime paths."""
import json, shutil
from pathlib import Path
import unreal as u

HERE = Path(__file__).parent
PROJECT = HERE.parents[1]
SKELETON = '/Game/Weapons/ASH12/Integrated20260917/SK_ASH12_Manny_Skeleton'
COMPRESSION = '/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'
ROOT = '/Game/Weapons/ASH12/UniversalAttachments20260919/Animations'
FAMILIES = ('vertical', 'canted', 'prism', 'angled')

JOBS = {}
for family in FAMILIES:
    JOBS[f'{family}/reload_empty'] = dict(
        dest=f'{ROOT}/{family}', name=f'A_ASH12_{family}_reload_empty',
        fbx=HERE / f'Animations/A_ASH12_{family}_reload_empty.fbx',
        tag='empty reload: right arm rebuilt from the original animation (original arm '
            'root, bend plane and bone rolls) joined to the accepted right-edge charging '
            'hand, with a minimal lens-clearing plane blend')
    JOBS[f'{family}/quick_melee'] = dict(
        dest=f'{ROOT}/{family}', name=f'A_ASH12_{family}_QuickCombat',
        fbx=HERE / f'Animations/A_ASH12_{family}_QuickCombat.fbx',
        tag='quick melee: rebuilt on the original animation (no 24 cm weapon shift, so the '
            'right arm no longer locks straight); the support arm bend plane is rotated by '
            'the least amount that keeps it out of the lens, hand and elbow angles untouched')

receipt_path = HERE / 'import_receipt_families.json'
receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Active play session; preserve it')
skeleton = u.load_asset(SKELETON)
compression = u.load_asset(COMPRESSION)
if not skeleton or not compression:
    raise RuntimeError('Missing skeleton or compression settings')
for key, job in JOBS.items():
    if key in receipt:
        continue
    if not job['fbx'].exists():
        raise RuntimeError('Missing authored FBX: ' + key)
    asset_path = f"{job['dest']}/{job['name']}"
    disk = PROJECT / 'Content' / Path(asset_path.removeprefix('/Game/') + '.uasset')
    backup = HERE / 'Before' / Path(asset_path.removeprefix('/Game/') + '.uasset')
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(disk, backup)
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh = False
    options.import_animations = True
    options.import_materials = False
    options.import_textures = False
    options.skeleton = skeleton
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 120)
    task = u.AssetImportTask()
    task.filename = str(job['fbx'])
    task.destination_path = job['dest']
    task.destination_name = job['name']
    task.options = options
    task.automated = True
    task.replace_existing = True
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Import produced no asset: ' + key)
    clip = u.load_asset(asset_path)
    clip.set_editor_property('bone_compression_settings', compression)
    if job.get('tag'):
        u.EditorAssetLibrary.set_metadata_tag(clip, 'Ash12CameraGuard', job['tag'])
    if not u.EditorLoadingAndSavingUtils.save_packages([clip.get_outer()], False):
        raise RuntimeError('Could not save ' + asset_path)
    receipt[key] = dict(asset=clip.get_path_name(), duration=clip.get_play_length(),
                        source_fbx=str(job['fbx']), backup=str(backup), game_tested=False)
    receipt_path.write_text(json.dumps(receipt, indent=2))
    print('ASH12_FAMILY_SAVED', key, clip.get_play_length(), flush=True)
print('ASH12_FAMILY_COMPLETE', len(receipt), flush=True)
