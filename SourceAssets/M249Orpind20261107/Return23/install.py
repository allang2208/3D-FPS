"""Save the two compact M249 side-reload tails and five existing grip profiles."""
from pathlib import Path
import unreal as u
import json, gzip, hashlib, zipfile

r = Path(__file__).resolve().parent
project = r.parents[2]
E = u.EditorAssetLibrary
profiles = {family: ('/Game/Weapons/M249/Bipod/DA_M249_SupportGrip' if family == 'base' else '/Game/Weapons/M249/CommonParts20261108/Profiles/DA_M249_'+family) for family in ('base','vertical','canted','prism','angled')}
motions = [json.load(gzip.open(f,'rt')) for f in sorted((r/'Motion').glob('*.json.gz'))]
targets = [m['asset'] for m in motions] + list(profiles.values())
receipt = r/'install_receipt.json'
report = dict(saved={}, animations=[], profiles=[], complete=False)


def disk(path):
    return project/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')


def sha(path):
    return hashlib.sha256(disk(path).read_bytes()).hexdigest()


def load(path):
    a = u.load_asset(path)
    if not a:
        raise RuntimeError('Missing '+path)
    return a


def save(a):
    if not E.save_loaded_asset(a,False):
        raise RuntimeError('Save '+a.get_path_name())
    path = a.get_path_name().split('.')[0]
    report['saved'][path] = sha(path)
    receipt.write_text(json.dumps(report,indent=2))


if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('PIE is running; stop PIE before saving the prepared M249 Return23 assets')
dirty = {a.get_path_name() for a in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(targets):
    raise RuntimeError('Unsaved target assets retained: '+str(sorted(dirty.intersection(targets))))
original = json.loads((r/'inputs.json').read_text())['hashes']
previous = json.loads(receipt.read_text())['saved'] if receipt.exists() else {}
for path, expected in original.items():
    if sha(path) != previous.get(path,expected):
        raise RuntimeError('Changed input retained: '+path)
if not (r/'Before.zip').exists():
    with zipfile.ZipFile(r/'Before.zip','w',zipfile.ZIP_DEFLATED) as z:
        for path in targets:
            z.write(disk(path),str(disk(path).relative_to(project)))

for data in motions:
    clip = load(data['asset'])
    ctl = clip.get_editor_property('controller')
    ctl.open_bracket('M249 compact left-hand return after magazine seating',False)
    try:
        ctl.set_frame_rate(u.FrameRate(numerator=data['fps'],denominator=1),False)
        ctl.set_number_of_frames(u.FrameNumber(value=round(data['duration']*data['fps'])),False)
        for bone, rows in data['tracks'].items():
            if not bone.endswith('_l'):
                raise RuntimeError('Out-of-scope bone '+bone)
            if not ctl.set_bone_track_keys(bone,[u.Vector(*v[:3]) for v in rows],[u.Quat(*v[3:7]) for v in rows],[u.Vector(*v[7:]) for v in rows],False):
                raise RuntimeError('Track '+bone)
    finally:
        ctl.close_bracket(False)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
        raise RuntimeError('Compression '+clip.get_path_name())
    save(clip)
    report['animations'].append(data['asset'])
    print('M249_RETURN23_ANIMATION_SAVED',clip.get_name(),flush=True)

for family, path in profiles.items():
    a = load(path)
    incoming = json.load(gzip.open(r/(family+'.json.gz'),'rt'))['clips']
    keys = {c['base'].split('.')[0] for c in incoming}
    rows, kept = [], []
    for c in a.get_editor_property('clips'):
        base, retained = c.get_editor_property('base'), c.get_editor_property('retained')
        if base.get_path_name().split('.')[0] in keys:
            continue
        if retained:
            kept.append((base,retained))
            continue
        rows.append(dict(base=base.get_path_name(),duration=c.get_editor_property('duration'),tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in c.get_editor_property('tracks')]))
    if not a.set_shared_clips_from_json(json.dumps(dict(family=family,clips=rows+incoming))):
        raise RuntimeError('Profile '+family)
    for base, retained in kept:
        a.keep_clip(base,retained)
    save(a)
    report['profiles'].append(path)
    print('M249_RETURN23_PROFILE_SAVED',family,flush=True)
report['complete'] = True
receipt.write_text(json.dumps(report,indent=2))
print('M249_RETURN23_SAVED',len(report['saved']),flush=True)
