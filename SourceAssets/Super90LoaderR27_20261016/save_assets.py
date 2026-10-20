"""Save the fourteen R27 loader clips (left arm + left fingers only) and their four grip entries.

Accepts only the installed R26b state recorded in r26b_saved_sha.json (clips) and
the R26b profile layers (float tolerance); anything else is left untouched."""
import json, hashlib, shutil
from pathlib import Path
import unreal as u

O = Path(__file__).parent
P = O.parents[1]
D = json.loads((O / 'animation_patch.json').read_text())
PREV = json.loads((O.parent / 'Super90LoaderR26_20261016/animation_patch.json').read_text())
PREV_SHA = json.loads((O / 'r26b_saved_sha.json').read_text())
E = u.EditorAssetLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE active; no assets changed')
receipt = dict(completed=False, revision=D['revision'], saved=[], runtime_tested=False)


def record():
    (O / 'save_receipt.json').write_text(json.dumps(receipt, indent=2))


def load(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing ' + path)
    return asset


def filename(path):
    return P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')


def backup(asset):
    src = filename(asset.get_path_name())
    dst = O / 'Before' / src.relative_to(P)
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + asset.get_path_name())
    receipt['saved'].append(asset.get_path_name())
    record()


def same_entry(current, expected, tolerance=1e-4):
    if current['base'] != expected['base'] or abs(current['duration'] - expected['duration']) > 1e-5:
        return False
    a = {t['bone']: t for t in current['tracks']}; b = {t['bone']: t for t in expected['tracks']}
    if set(a) != set(b):
        return False
    for bone, t in a.items():
        e = b[bone]
        if len(t['times']) != len(e['times']) or len(t['values']) != len(e['values']):
            return False
        if any(abs(x - y) > tolerance for x, y in zip(t['times'], e['times'])) or \
           any(abs(x - y) > tolerance for x, y in zip(t['values'], e['values'])):
            return False
    return True


def merge_profile(asset, family):
    # Return plain values before replacing the reflected USTRUCT array.
    payload = dict(family=str(asset.get_editor_property('family')), clips=[])
    retained, found = {}, set()
    patch = D['profiles'][family]['clips']
    for c in asset.get_editor_property('clips'):
        path = c.get_editor_property('base').get_path_name()
        current = dict(base=path, duration=float(c.get_editor_property('duration')),
            tracks=[dict(bone=str(t.get_editor_property('bone')), times=list(t.get_editor_property('times')),
                         values=list(t.get_editor_property('values'))) for t in c.get_editor_property('tracks')])
        old = c.get_editor_property('retained')
        if path in patch:
            if old or not same_entry(current, PREV['profiles'][family]['clips'][path]):
                raise RuntimeError('Target profile is not the installed R26b entry: ' + family + ' ' + path)
            payload['clips'].append(patch[path])
            found.add(path)
        else:
            payload['clips'].append(current)
            if old:
                retained[path] = old.get_path_name()
    if found != set(patch):
        raise RuntimeError('Missing loader profile entries: ' + family)
    return payload, retained


targets = {s['path'].split('.')[0] for s in D['clips'].values()} | {s['path'].split('.')[0] for s in D['profiles'].values()}
dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in targets]
if dirty:
    raise RuntimeError('Preserve unsaved targets: ' + str(dirty))
clips, profiles = {}, {}
for role, spec in D['clips'].items():
    if hashlib.sha256(filename(spec['path']).read_bytes()).hexdigest() != PREV_SHA[spec['path']]:
        raise RuntimeError('Animation is not the installed R26b package: ' + role)
    clip = load(spec['path'])
    backup(clip)
    clips[role] = clip
for family, spec in D['profiles'].items():
    asset = load(spec['path'])
    payload, retained = merge_profile(asset, family)
    backup(asset)
    profiles[family] = (asset, payload, retained)
record()
for role, clip in clips.items():
    spec = D['clips'][role]
    controller = clip.get_editor_property('controller')
    controller.open_bracket('Super90 loader R27 left hand', False)
    try:
        controller.set_frame_rate(u.FrameRate(D['fps'], 1), False)
        controller.set_number_of_frames(u.FrameNumber(spec['frames']), False)
        for track in spec['tracks']:
            if track['bone'] not in D['write_bones']:
                continue
            keys = [track['values'][i:i+10] for i in range(0, len(track['values']), 10)]
            if len(keys) == 1:
                keys *= spec['frames'] + 1
            if not controller.set_bone_track_keys(track['bone'], [u.Vector(*v[:3]) for v in keys],
                    [u.Quat(*v[3:7]) for v in keys], [u.Vector(*v[7:]) for v in keys], False):
                raise RuntimeError('Cannot write ' + role + ' ' + track['bone'])
    finally:
        controller.close_bracket(False)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
        raise RuntimeError('Animation finalization failed: ' + role)
    E.set_metadata_tag(clip, 'Super90LoaderR26', D['revision'])
    E.set_metadata_tag(clip, 'Super90LoaderR26Authoring', str(O / 'author_r27.py'))
    save(clip)
for family, (asset, payload, retained) in profiles.items():
    if not asset.set_shared_clips_from_json(json.dumps(payload)):
        raise RuntimeError('Cannot apply grip deltas: ' + family)
    if retained:
        entries = list(asset.get_editor_property('clips'))
        for i, entry in enumerate(entries):
            path = entry.get_editor_property('base').get_path_name()
            if path in retained:
                entry.set_editor_property('retained', load(retained[path]))
                entries[i] = entry
        asset.set_editor_property('clips', entries)
    E.set_metadata_tag(asset, 'Super90LoaderR26', D['revision'] + '; loader normal/empty 1-7 left hand tracks only')
    save(asset)
receipt['completed'] = True
record()
print('SUPER90_LOADER_R27_SAVED', len(receipt['saved']), 'assets; no gameplay test', flush=True)
