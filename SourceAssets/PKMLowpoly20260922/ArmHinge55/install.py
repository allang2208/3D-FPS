"""ArmHinge55 install: rewrite only the seven left-arm skin bone tracks
(upperarm_l, upperarm_twist_01/02_l, lowerarm_l, lowerarm_twist_02/01_l, hand_l local) in
every collected PKM / 201 clip.  The hand world matrix, fingers, right arm, weapon, belt and
all other tracks keep their saved keys.

Stops before writing if PIE is running, a target has unsaved editor changes, or a package
changed after collect.py read it.  Backups go to Before/, the receipt to delivery.json, and a
package whose bytes do not change after saving is an error.
"""
import unreal as u, json, gzip, hashlib, shutil
from pathlib import Path

HERE = Path(globals().get('__file__') or r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\ArmHinge55\install.py').resolve().parent
PROJECT = HERE.parents[2]
E = u.EditorAssetLibrary
BATCH = 200 if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower() else 6
if Path(u.SystemLibrary.convert_to_absolute_path(u.Paths.project_dir())).resolve() != PROJECT.resolve():
    raise RuntimeError('Editor project is %s, not %s; no asset changes made' % (u.Paths.project_dir(), PROJECT))
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE active; no asset changes made')
index = {g: v for g, v in json.loads((HERE / 'inputs.json').read_text()).items() if isinstance(v, dict) and 'clips' in v}
authoring = json.loads((HERE / 'authoring.json').read_text())
receipt_path = HERE / 'delivery.json'
previous = json.loads((HERE / 'delivery_v1.json').read_text())['saved'] if (HERE / 'delivery_v1.json').exists() else {}
receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
if receipt.get('revision') != 'ArmHinge55b':
    receipt = {'revision': 'ArmHinge55b', 'saved': {}, 'runtime_tested': False, 'previous_receipt': 'delivery_v1.json'}


def disk(p):
    return PROJECT / 'Content' / (p.split('.')[0].removeprefix('/Game/') + '.uasset')


def sha(p):
    return hashlib.sha256(disk(p).read_bytes()).hexdigest()


def record():
    receipt_path.write_text(json.dumps(receipt, indent=1))


todo = [(g, k, c) for g in index for k, c in index[g]['clips'].items() if k not in receipt['saved']]
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for g, k, c in todo:
    if k in dirty:
        raise RuntimeError('Unsaved editor changes: ' + k)
    expected = previous[k]['sha256'] if k in previous else c['sha256']   # the v1 result, or the collected bytes
    if sha(k) != expected:
        raise RuntimeError('Changed after collect / ArmHinge55 v1 (re-run collect/author): ' + k)
written = 0
for g, k, c in todo:
    if written >= BATCH:
        break
    a = authoring[k]
    with gzip.open(a['tracks'], 'rt', encoding='utf8') as f:
        data = json.load(f)
    if data['source_sha256'] != c['sha256']:
        raise RuntimeError('Authored from another version: ' + k)
    backup = HERE / 'Before' / disk(k).relative_to(PROJECT / 'Content')
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(disk(k), backup)
    before = sha(k)
    clip = u.load_asset(k)
    ctl = clip.get_editor_property('controller')
    ctl.open_bracket('ArmHinge55: anatomical left upper arm / forearm pronation', False)
    try:
        for n, rows in data['tracks'].items():
            if len(rows) != c['keys']:
                raise RuntimeError('Key count mismatch %s %s' % (k, n))
            if not ctl.set_bone_track_keys(n, [u.Vector(*v[:3]) for v in rows], [u.Quat(*v[3:7]) for v in rows],
                                           [u.Vector(*v[7:10]) for v in rows], False):
                raise RuntimeError('Cannot write %s %s' % (k, n))
    finally:
        ctl.close_bracket(False)
    E.set_metadata_tag(clip, 'ArmHingeRevision', 'ArmHinge55b: upper-arm helpers on the anatomical elbow hinge (+20 deg crease calibration); forearm pronation ramp (cap 110 deg); elbow <=6 cm')
    u.AKMAnimationAuditLibrary.finish_animation_compression(clip)
    if not E.save_loaded_asset(clip, False):
        raise RuntimeError('Cannot save ' + k)
    after = sha(k)
    if after == before:
        raise RuntimeError('Package unchanged after save: ' + k)
    receipt['saved'][k] = {'before_sha256': before, 'sha256': after, 'backup': str(backup), 'keys': c['keys']}
    record()
    written += 1
    print('ARMHINGE55_SAVED', k, flush=True)
left = sum(1 for g in index for k in index[g]['clips'] if k not in receipt['saved'])
receipt['status'] = 'complete' if not left else 'partial'
record()
print('ARMHINGE55_COMPLETE' if not left else 'ARMHINGE55_PARTIAL %d left' % left, len(receipt['saved']), flush=True)
