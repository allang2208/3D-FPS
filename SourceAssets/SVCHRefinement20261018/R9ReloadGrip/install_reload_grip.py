"""Save only the two reload left-arm corrections into the installed SVCH profile."""
import gzip
import hashlib
import json
import shutil
from pathlib import Path

import unreal as u

O = Path(__file__).parent
P = Path(u.Paths.project_dir()).resolve()
inputs = json.loads((O / 'Inputs/manifest.json').read_text())
motion = json.load(gzip.open(O / 'Inputs/motion.json.gz', 'rt'))
before = json.loads((O / 'Inputs/profile_before.json').read_text())
source = O / 'profile_reload_grip.json'
after = json.loads(source.read_text())
allowed = {'clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l', 'upperarm_twist_01_l',
           'upperarm_twist_02_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l'}
reloads = {motion['clips'][r]['path'] for r in ('reload', 'reload_empty')}


def disk(path):
    return P / 'Content' / (path.removeprefix('/Game/').split('.')[0] + '.uasset')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Preserve parallel edits and the accepted mesh/animation dependencies before
# touching the profile. These are write guards, not gameplay acceptance tests.
for spec in [*inputs.values(), *motion['clips'].values()]:
    if digest(disk(spec['path'])) != spec['sha256']:
        raise RuntimeError('Source changed since authoring; preserve: ' + spec['path'])
if before['family'] != after['family'] or len(before['clips']) != len(after['clips']):
    raise RuntimeError('Unexpected profile scope')
for old, new in zip(before['clips'], after['clips']):
    if old['base'] not in reloads:
        if old != new:
            raise RuntimeError('Non-reload clip changed: ' + old['base'])
    else:
        if old['base'] != new['base'] or old['duration'] != new['duration']:
            raise RuntimeError('Source clip/clock changed')
        keep = lambda c: [t for t in c['tracks'] if t['bone'] not in allowed]
        if keep(old) != keep(new):
            raise RuntimeError('Right/finger/mechanical tracks changed')
path = inputs['profile']['path']
package = disk(path)
for dirty in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if dirty.get_path_name() == path:
        raise RuntimeError('Preserve unsaved profile edits: ' + path)
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Preserve the active game world; defer asset save')
backup = O / 'Before'
backup.mkdir(exist_ok=True)
backup_file = backup / package.name
if backup_file.exists():
    raise RuntimeError('Prior install exists; preserve its backup and receipt')
shutil.copy2(package, backup_file)
profile = u.load_asset(path)
if not profile.set_shared_clips_from_json(source.read_text()):
    raise RuntimeError('Profile import failed')
u.EditorAssetLibrary.set_metadata_tag(profile, 'SVCHReloadGrip',
    'R9: accepted native V9/SVD front-half magazine grasp; shared normal/empty registration; native fingers and clocks preserved')
if not u.EditorAssetLibrary.save_loaded_asset(profile, False):
    raise RuntimeError('Profile save failed')
receipt = {
    'revision': 'R9ReloadGrip', 'saved': True, 'profile': profile.get_path_name(),
    'previous_profile_sha256': inputs['profile']['sha256'], 'profile_sha256': digest(package),
    'profile_source_sha256': digest(source), 'changed_actions': ['reload', 'reload_empty'],
    'changed_bones': sorted(allowed), 'other_ten_clips_preserved': True,
    'source_animation_assets_modified': False, 'native_v9_mesh_modified': False,
    'native_finger_tracks_modified': False, 'right_arm_tracks_modified': False,
    'mechanical_tracks_and_source_clocks_modified': False,
    'mesh': inputs['svch']['path'], 'native_v9_skin': inputs['arms']['path'],
    'runtime_tested': False, 'visual_acceptance': 'User review pending', 'backup': str(backup_file)
}
(O / 'install_receipt.json').write_text(json.dumps(receipt, indent=2))
print('SVCH_RELOAD_GRIP_SAVED', json.dumps(receipt), flush=True)
