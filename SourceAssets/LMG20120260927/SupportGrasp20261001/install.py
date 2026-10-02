"""Save the authored no-grip 201 corrections as the existing runtime profile type."""
import gzip
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
ASSET = '/Game/Weapons/AnimationProfiles20261001/ue_lmg201/DA_base'
E = u.EditorAssetLibrary
with gzip.open(HERE / 'profile.json.gz', 'rt', encoding='utf8') as f:
    data = json.load(f)

def disk(path):
    return PROJECT / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')

if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve() != PROJECT:
    raise RuntimeError('Wrong project; no profile saved')
headless = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not headless and u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE active; preserve loaded assets')
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if ASSET in dirty:
    raise RuntimeError('Preserve unsaved profile: ' + ASSET)
for key, spec in data['clips'].items():
    if hashlib.sha256(disk(key).read_bytes()).hexdigest() != spec['source_sha256']:
        raise RuntimeError('Source changed during authoring: ' + key)

profile = u.load_asset(ASSET) if E.does_asset_exist(ASSET) else None
if profile:
    backup = HERE / 'Before/DA_base.uasset'
    if not backup.exists():
        backup.parent.mkdir(exist_ok=True)
        shutil.copy2(disk(ASSET), backup)
else:
    factory = u.DataAssetFactory()
    factory.set_editor_property('data_asset_class', u.WeaponGripProfile)
    profile = u.AssetToolsHelpers.get_asset_tools().create_asset('DA_base', ASSET.rsplit('/', 1)[0], u.WeaponGripProfile, factory)
if not profile:
    raise RuntimeError('Cannot create 201 base profile')

count = 0
for key, spec in data['clips'].items():
    base = u.load_asset(key)
    # Native profile fields are read-only. Use its existing BakeClip authoring
    # API with an unsaved working copy; only the compact profile is published.
    working_path = '/Game/Weapons/LMG201/SupportGrasp20261001/Working/' + key.split('/LMG201/')[1].replace('/', '__')
    authored = E.duplicate_asset(key, working_path)
    if not authored:
        raise RuntimeError('Could not create working pose: ' + key)
    controller = authored.get_editor_property('controller')
    controller.open_bracket('201 no-grip support grasp', False)
    try:
        for bone, rows in spec['authored_tracks'].items():
            if not controller.set_bone_track_keys(bone, [u.Vector(*r[:3]) for r in rows],
                    [u.Quat(*r[3:7]) for r in rows], [u.Vector(*r[7:10]) for r in rows], False):
                raise RuntimeError('Could not author ' + key + ' / ' + bone)
    finally:
        controller.close_bracket(False)
    u.AKMAnimationAuditLibrary.finish_animation_compression(authored)
    if not profile.bake_clip(base, authored):
        raise RuntimeError('Could not bake profile: ' + key)
    count += 1
    print('SUPPORTGRASP_PROFILE_CLIP', key, flush=True)
profile.set_editor_property('family', 'base')
E.set_metadata_tag(profile, 'SupportGraspRevision', 'SupportGrasp20261001: native SVD support orientation, M4 natural distal curl, fitted to the closed 201 handguard')
if not E.save_loaded_asset(profile, False):
    raise RuntimeError('Could not save ' + ASSET)
(HERE / 'delivery.json').write_text(json.dumps({'revision': data['revision'], 'asset': ASSET,
    'saved': True, 'clips': count, 'source_animations_changed': False, 'runtime_tested': False,
    'temporary_authored_sequences_saved': False}, indent=1))
print('SUPPORTGRASP_PROFILE_SAVED', ASSET, count, flush=True)
