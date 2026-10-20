"""Install the bounded reload revision after preserving the current R9 profile."""
import gzip, hashlib, json, shutil
from pathlib import Path
import unreal as u

O = Path(__file__).parent
R9 = O.parent / 'R9ReloadGrip'
P = Path(u.Paths.project_dir()).resolve()
source = O / 'profile_native_registration.json'
inputs = json.loads((R9 / 'Inputs/manifest.json').read_text())
motion = json.load(gzip.open(R9 / 'Inputs/motion.json.gz', 'rt'))
prior_receipt = O / 'install_receipt.json'
prior = json.loads((prior_receipt if prior_receipt.exists() else R9 / 'install_receipt.json').read_text())
path = inputs['profile']['path']
disk = lambda name: P / 'Content' / (name.removeprefix('/Game/').split('.')[0] + '.uasset')
digest = lambda file: hashlib.sha256(file.read_bytes()).hexdigest()
old = json.loads((R9 / 'profile_reload_grip.json').read_text())
new = json.loads(source.read_text())
reloads = {motion['clips'][name]['path'] for name in ('reload', 'reload_empty')}
allowed = {'clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l', 'upperarm_twist_01_l',
           'upperarm_twist_02_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l'}
for a, b in zip(old['clips'], new['clips']):
    if a['base'] not in reloads:
        assert a == b, 'Preserve other actions'
    else:
        assert a['base'] == b['base'] and a['duration'] == b['duration'], 'Preserve clocks'
        keep = lambda c: [t for t in c['tracks'] if t['bone'] not in allowed]
        assert keep(a) == keep(b), 'Preserve right arm, native fingers and mechanics'
for key, spec in inputs.items():
    if key != 'profile':
        assert digest(disk(spec['path'])) == spec['sha256'], 'Source changed: ' + spec['path']
for spec in motion['clips'].values():
    assert digest(disk(spec['path'])) == spec['sha256'], 'Animation source changed'
package = disk(path)
assert digest(package) == prior['profile_sha256'], 'Preserve parallel profile changes'
assert not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world(), 'Preserve active game'
assert all(p.get_path_name() != path for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()), 'Preserve unsaved profile'
backup = O / 'Before'
backup.mkdir(exist_ok=True)
backup_file = backup / (package.stem + '_' + prior['profile_sha256'][:12] + package.suffix)
assert not backup_file.exists(), 'Preserve previous install'
shutil.copy2(package, backup_file)
if prior_receipt.exists():
    shutil.copy2(prior_receipt, backup / ('install_' + prior['profile_sha256'][:12] + '.json'))
profile = u.load_asset(path)
assert profile.set_shared_clips_from_json(source.read_text()), 'Profile import failed'
u.EditorAssetLibrary.set_metadata_tag(profile, 'SVCHReloadGrip',
    'R10: native V9 rigid arm; closed-shell magazine clearance; native wrist and finger locals preserved')
assert u.EditorAssetLibrary.save_loaded_asset(profile, False), 'Asset save failed'
receipt = {'saved': True, 'revision': 'R10ReloadReview', 'profile': profile.get_path_name(),
           'profile_sha256': digest(package), 'source_sha256': digest(source),
           'previous_profile_sha256': prior['profile_sha256'], 'changed_actions': ['reload', 'reload_empty'],
           'native_v9_mesh_unchanged': True, 'source_animations_unchanged': True,
           'native_wrist_and_finger_locals_preserved': True, 'runtime_review_pending': True}
(O / 'install_receipt.json').write_text(json.dumps(receipt, indent=2))
print('SVCH_R10_PROFILE_SAVED', json.dumps(receipt), flush=True)
