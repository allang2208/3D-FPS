"""Save the ten ClothReload44 reload clips into their own package folder.

Runs inside UE (commandlet or the existing editor bridge).  Stops before writing
if PIE is running, a target is dirty, or a grip-family idle changed after the
tracks were authored.  ClothFeed33 assets are left untouched for rollback; the
runtime switches only through LMG201WeaponAssets::ClothAnimationPath.
A new motion.json revision starts a new receipt and overwrites the clips in place
(the previous packages are in Before_v1/ with hashes).  At most BATCH clips are
written per call so each bridge call stays short; call again until COMPLETE.
"""
import unreal as u, json, gzip, hashlib
from pathlib import Path

O = Path(globals().get('__file__') or r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44\install.py').parent
BATCH = 10 if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower() else 2
PROJECT = O.parents[2]
E = u.EditorAssetLibrary
BODY = '/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE active; no asset changes made')
motion = json.loads((O / 'motion.json').read_text())
receipt_path = O / 'delivery.json'



def record():
    receipt_path.write_text(json.dumps(receipt, indent=2))


def file(p):
    return PROJECT / 'Content' / (p.split('.')[0].removeprefix('/Game/') + '.uasset')


def sha(p):
    return hashlib.sha256(file(p).read_bytes()).hexdigest()


receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
only = set(motion.get('install_only') or motion['clips'])
if receipt.get('revision') != motion['revision']:
    previous = receipt
    receipt = {'revision': motion['revision'], 'status': 'installing', 'saved': {}, 'tested': False,
               'previous_receipt': 'Before_v3/delivery_v3.json', 'install_only': sorted(only)}
    # clips not re-authored in this revision keep their saved packages
    for key, spec in motion['clips'].items():
        old = previous.get('saved', {}).get(spec['destination'])
        if key not in only and old and old['sha256'] == sha(spec['destination']):
            receipt['saved'][spec['destination']] = dict(old, carried_from=previous.get('revision'))


dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for key, spec in motion['clips'].items():
    if spec['destination'] in dirty:
        raise RuntimeError('Target has unsaved editor changes: ' + spec['destination'])
    if sha(spec['idle_source']) != spec['idle_sha256']:
        raise RuntimeError('Idle changed after authoring (%s); re-run collect/author first' % spec['idle_source'])
body = u.load_asset(BODY)
written = 0
for key, spec in motion['clips'].items():
    path = spec['destination']
    if path in receipt['saved'] or key not in only:
        continue
    if written >= BATCH:
        break
    before = sha(path) if file(path).exists() else None
    clip = u.load_asset(path) or E.duplicate_asset(spec['idle_source'], path)
    if not clip:
        raise RuntimeError('Cannot create ' + path)
    with gzip.open(spec['keys'], 'rt', encoding='utf8') as f:
        tracks = json.load(f)
    c = clip.get_editor_property('controller')
    c.open_bracket('201 cloth pouch reload: ClothReload44 prop-contact keys', False)
    try:
        c.remove_all_bone_tracks(False)
        c.set_frame_rate(u.FrameRate(numerator=spec['fps'], denominator=1), False)
        c.set_number_of_frames(u.FrameNumber(value=spec['frames'] - 1), False)
        for n, rows in tracks.items():
            if not c.add_bone_curve(n, False):
                raise RuntimeError('Cannot create track ' + n)
            if not c.set_bone_track_keys(n, [u.Vector(*v[:3]) for v in rows], [u.Quat(*v[3:7]) for v in rows],
                                         [u.Vector(*v[7:10]) for v in rows], False):
                raise RuntimeError('Cannot write ' + n)
    finally:
        c.close_bracket(False)
    clip.set_preview_skeletal_mesh(body)
    E.set_metadata_tag(clip, '201ReloadRevision', motion['revision'] + ': reference-video phases; PKM reload hand orientations; '
                       'PKM LeftArm48 coherent arm segments; elbow on the shoulder-wrist circle; right grip follows gun')
    E.set_metadata_tag(clip, '201AuthoringSource', spec['keys'])
    if spec.get('belt_fit'):
        E.set_metadata_tag(clip, '201BeltFitRevision', spec['belt_fit'])
    E.set_metadata_tag(clip, '201ReferenceVideo', motion['reference_video'])
    u.AKMAnimationAuditLibrary.finish_animation_compression(clip)
    if not E.save_loaded_asset(clip, False):
        raise RuntimeError('Cannot save ' + path)
    after = sha(path)
    if after == before:
        raise RuntimeError('Package unchanged after save: ' + path)
    receipt['saved'][path] = {'sha256': after, 'previous_sha256': before, 'frames': spec['frames'], 'seconds': spec['seconds'], 'keys': spec['keys']}
    record()
    written += 1
    print('RELOAD44_SAVED', key, flush=True)
if any(motion['clips'][k]['destination'] not in receipt['saved'] for k in only):
    print('RELOAD44_PARTIAL', len(receipt['saved']), flush=True)
else:
    receipt.update(status='animations_saved', phases=motion['phases'], runtime_tested=False)
    record()
    print('RELOAD44_COMPLETE', len(receipt['saved']), flush=True)
