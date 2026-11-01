"""Save only the post-release follow-through; leave the charge asset untouched."""
import datetime
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
R = P.parents[2]
D = '/Game/Weapons/ThunderGodHammer20261028/ThunderThrowV1'
if Path(u.Paths.project_dir()).resolve() != R:
    raise RuntimeError('Wrong project')
motion = json.loads((P / 'motion.json').read_text(encoding='utf-8'))
clips = {}
prior = json.loads((P / 'BeforeImport-20261029-100331/manifest.json').read_text(encoding='utf-8'))
known_disk = {Path(row['file']).name: row['sha256'] for row in prior}
dirty = {package.get_path_name() for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for name in motion['clips']:
    clip = u.load_asset(D + '/' + name)
    if not clip:
        raise RuntimeError('Missing current animation: ' + name)
    revision = u.EditorAssetLibrary.get_metadata_tag(clip, 'ThunderThrowRevision')
    file = R / 'Content/Weapons/ThunderGodHammer20261028/ThunderThrowV1' / (name + '.uasset')
    unchanged_disk = hashlib.sha256(file.read_bytes()).hexdigest() == known_disk.get(file.name)
    import_data = clip.get_editor_property('asset_import_data')
    imported_source = Path(import_data.get_first_filename()).resolve() if import_data else None
    owned_source = imported_source in {
        (P / 'Export' / (name + '.fbx')).resolve(),
        (P.parent / 'ChargeRestoreV6/Export' / (name + '.fbx')).resolve()
    }
    if D + '/' + name in dirty:
        raise RuntimeError('Target has unsaved editor changes: ' + name)
    # An editor started before the last commandlet can still hold an older,
    # untagged package. Reimport this owned clip only when the saved file still
    # matches the V6 input backed up before this task's first import.
    if not revision.startswith(('ChargeRestoreV6:', 'ThrowFollowThroughV7:')) and not (not revision and (unchanged_disk or owned_source)):
        raise RuntimeError('Current animation is no longer the expected V6: ' + name + ' ' + revision)
    clips[name] = clip

backup = P / ('BeforeImport-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir()
manifest = []
for name in motion['clips']:
    source = R / 'Content/Weapons/ThunderGodHammer20261028/ThunderThrowV1' / (name + '.uasset')
    shutil.copy2(source, backup / source.name)
    manifest.append({'file': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()})
(backup / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
receipt = {'complete': False, 'saved': [], 'backup': str(backup), 'runtime_tested': False,
           'preview_rendered': False, 'charge': 'untouched ChargeRestoreV6', 'preserved_throw_seconds': .24}
def record():
    (P / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
record()

arms = u.load_asset('/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1')
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
asset_tools = u.AssetToolsHelpers.get_asset_tools()
for name in motion['clips']:
    opt = u.FbxImportUI()
    opt.automated_import_should_detect_type = False
    opt.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh = False
    opt.import_animations = True
    opt.import_materials = False
    opt.import_textures = False
    opt.skeleton = arms.get_editor_property('skeleton')
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
    opt.anim_sequence_import_data.set_editor_property('custom_sample_rate', 240)
    task = u.AssetImportTask()
    task.filename = str(P / 'Export' / (name + '.fbx'))
    task.destination_path = D
    task.destination_name = name
    task.automated = True
    task.save = False
    task.replace_existing = True
    task.replace_existing_settings = True
    task.options = opt
    asset_tools.import_asset_tasks([task])
    clip = u.load_asset(D + '/' + name)
    if not clip or not task.imported_object_paths:
        raise RuntimeError('Import failed: ' + name)
    clip.set_editor_property('bone_compression_settings', u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
    clip.set_editor_property('rate_scale', 1.)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
        raise RuntimeError('Finalize failed: ' + name)
    u.EditorAssetLibrary.set_metadata_tag(clip, 'ThunderThrowRevision',
        'ThrowFollowThroughV7: continuous post-release swing, staggered exits, trailing wrists; charge unchanged')
    if not u.EditorLoadingAndSavingUtils.save_packages([clip.get_outermost()], False):
        raise RuntimeError('Save failed: ' + name)
    receipt['saved'].append(clip.get_path_name())
    record()
receipt['complete'] = True
record()
print('THUNDER_FOLLOW_THROUGH_V7_SAVED', flush=True)

# Read the saved native surface and sequence data for the requested diagnosis.
import runpy
runpy.run_path(str(P / "read_assets.py"), run_name="__main__")
