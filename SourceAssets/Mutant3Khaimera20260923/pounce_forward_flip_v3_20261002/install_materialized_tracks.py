"""Save the already imported two-wrist data after the offline file-lock interruption."""
import hashlib
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).parent
PROJECT = Path(u.Paths.project_dir()).resolve()
CONTRACT = json.loads((ROOT / 'animation_contract.json').read_text(encoding='utf-8'))
PATCHES = json.loads((ROOT / 'production_hand_keys.json').read_text(encoding='utf-8'))
STATE = json.loads((ROOT / 'install_state.json').read_text(encoding='utf-8'))
TARGETS = {role: '/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations/A_Mutant3_' + role
           for role in CONTRACT['clips']}

def record():
    (ROOT / 'install_state.json').write_text(json.dumps(STATE, indent=2), encoding='utf-8')

if STATE['saved']:
    raise RuntimeError('This installation already saved production assets; do not replay it')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('End existing PIE before changing or saving the production animation packages')
dirty = {package.get_path_name() for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if set(TARGETS.values()) & dirty:
    raise RuntimeError('A production pounce animation has unsaved changes; left untouched')
targets = {}
for role, path in TARGETS.items():
    file = PROJECT / 'Content' / Path(path.removeprefix('/Game/')).with_suffix('.uasset')
    if hashlib.sha256(file.read_bytes()).hexdigest() != CONTRACT['source_sha256'][role]:
        raise RuntimeError('Production animation changed since materializing the wrist data: ' + path)
    target = u.load_asset(path)
    if not isinstance(target, u.AnimSequence):
        raise RuntimeError('Production animation is unavailable: ' + path)
    count = target.get_editor_property('data_model_interface').get_number_of_keys()
    if set(PATCHES[role]) != {'LeftHand', 'RightHand'}:
        raise RuntimeError('This patch must contain only the two wrist tracks')
    for keys in PATCHES[role].values():
        if any(len(keys[channel]) != count for channel in ('p', 'q', 's')):
            raise RuntimeError('Materialized wrist key count differs from production: ' + role)
    targets[role] = target

STATE['state'] = 'saving materialized wrist rotations through existing editor'
STATE['installation_backend'] = 'existing editor Python bridge, batch mutex'
STATE.pop('error', None)
record()
try:
    for role, target in targets.items():
        controller = target.get_editor_property('controller')
        controller.open_bracket('Mutant3 reverse both palms and hand directions before takeoff', False)
        try:
            for name, keys in PATCHES[role].items():
                if not controller.set_bone_track_keys(
                        name, [u.Vector(*key) for key in keys['p']],
                        [u.Quat(*key) for key in keys['q']],
                        [u.Vector(*key) for key in keys['s']], False):
                    raise RuntimeError('Could not write wrist track ' + role + '/' + name)
        finally:
            controller.close_bracket(False)
        u.EditorAssetLibrary.set_metadata_tag(target, 'PounceHandRevision', CONTRACT['revision'])
        u.EditorAssetLibrary.set_metadata_tag(target, 'PounceHandAuthorSource', str(ROOT / 'production_hand_keys.json'))
        if not u.EditorAssetLibrary.save_loaded_asset(target, False):
            raise RuntimeError('Could not save production animation ' + TARGETS[role])
        STATE['saved'].append({'asset': target.get_path_name(), 'rotation_tracks': 2,
                               'seconds': CONTRACT['clips'][role]['seconds']})
        record()
        u.log('MUTANT3_FORWARD_FLIP_SAVED ' + role)
    STATE['state'] = 'Three production pounce clips saved; testing left to the user'
    CONTRACT['state'] = STATE['state']
    (ROOT / 'animation_contract.json').write_text(json.dumps(CONTRACT, indent=2), encoding='utf-8')
    record()
    u.log('MUTANT3_FORWARD_FLIP_INSTALL_COMPLETE 3 production clips')
except Exception as error:
    STATE['state'] = 'installation interrupted'
    STATE['error'] = str(error)
    record()
    raise
