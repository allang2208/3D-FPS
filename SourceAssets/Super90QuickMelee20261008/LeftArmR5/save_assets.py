"""Write only the seven authored left-chain tracks and matching grip deltas."""
import json
import shutil
from pathlib import Path
import unreal as u

O = Path(__file__).parent
P = O.parents[2]
D = json.loads((O / 'animation_patch.json').read_text())
E = u.EditorAssetLibrary
WRITE = set(D['write_bones'])
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE active; no assets changed')
receipt = dict(completed=False, revision=D['revision'], saved=[],
               bones=D['write_bones'], runtime_tested=False)

def record():
    (O / 'save_receipt.json').write_text(json.dumps(receipt, indent=2))

def load(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing ' + path)
    return asset

def backup(asset):
    rel = asset.get_path_name().split('.')[0].removeprefix('/Game/') + '.uasset'
    src, dst = P / 'Content' / rel, O / 'Before/Content' / rel
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + asset.get_path_name())
    receipt['saved'].append(asset.get_path_name())
    record()

def merge_profile(asset, patch):
    # Copy reflected data into plain Python values, then leave this function
    # before replacing the USTRUCT array (views into it become invalid).
    payload = dict(family=str(asset.get_editor_property('family')), clips=[])
    retained = {}
    found = False
    for clip in asset.get_editor_property('clips'):
        base = clip.get_editor_property('base').get_path_name()
        tracks = [dict(bone=str(t.get_editor_property('bone')),
                       times=list(t.get_editor_property('times')),
                       values=list(t.get_editor_property('values')))
                  for t in clip.get_editor_property('tracks')]
        old = clip.get_editor_property('retained')
        if old:
            retained[base] = old.get_path_name()
        if base == D['melee_path']:
            if old:
                raise RuntimeError('Melee changed to a retained clip; preserve current profile')
            tracks = [t for t in tracks if t['bone'] not in WRITE]
            tracks += [t for t in patch['tracks'] if t['bone'] in WRITE]
            found = True
        payload['clips'].append(dict(base=base, duration=float(clip.get_editor_property('duration')),
                                     tracks=tracks))
    if not found:
        raise RuntimeError('Installed quick-melee profile entry is missing')
    return payload, retained

clip = load(D['melee_path'])
if abs(clip.get_play_length() - D['duration']) > .0001:
    raise RuntimeError('Source duration changed since authoring; preserve current animation')
backup(clip)
profiles = {}
for family, spec in D['profiles'].items():
    asset = load(spec['path']); backup(asset)
    payload, retained = merge_profile(asset, spec['clip'])
    profiles[family] = (asset, payload, retained)
record()
controller = clip.get_editor_property('controller')
controller.open_bracket('Super90 wrist-first arm solve and torso-side left shoulder', False)
try:
    for track in D['base_tracks']:
        if track['bone'] not in WRITE:
            continue
        keys = [track['values'][i:i+10] for i in range(0, len(track['values']), 10)]
        if len(keys) == 1:
            keys *= D['frames'] + 1
        if not controller.set_bone_track_keys(track['bone'], [u.Vector(*v[:3]) for v in keys],
                                              [u.Quat(*v[3:7]) for v in keys],
                                              [u.Vector(*v[7:]) for v in keys], False):
            raise RuntimeError('Cannot write ' + track['bone'])
finally:
    controller.close_bracket(False)
if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
    raise RuntimeError('Animation finalization failed')
E.set_metadata_tag(clip, 'Super90QuickMeleeSource', D['revision'] + '; left chain only; R3 gun and palms retained')
E.set_metadata_tag(clip, 'Super90QuickMeleeAuthoringScript', str(O / 'author_motion.py'))
save(clip)
for family, (asset, payload, retained) in profiles.items():
    if not asset.set_shared_clips_from_json(json.dumps(payload)):
        raise RuntimeError('Cannot save left-arm grip deltas: ' + family)
    if retained:
        rows = list(asset.get_editor_property('clips'))
        for i, row in enumerate(rows):
            path = row.get_editor_property('base').get_path_name()
            if path in retained:
                row.set_editor_property('retained', load(retained[path]))
                rows[i] = row
        asset.set_editor_property('clips', rows)
    E.set_metadata_tag(asset, 'Super90QuickMeleeSource', D['revision'] + '; only left-arm melee deltas updated')
    save(asset)
receipt['completed'] = True
record()
print('SUPER90_LEFT_ARM_SAVED', len(receipt['saved']), 'assets; no gameplay test', flush=True)
