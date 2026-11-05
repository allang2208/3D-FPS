"""Read current male/female weapon clips for the requested contact investigation.

Runs through the existing editor Python gate; writes only this task's inputs.
"""
import hashlib
import json
import time
from pathlib import Path
import os
import unreal as u

P = Path(os.environ['FPSGAME_PROJECT']).resolve()
W = Path(__file__).resolve().parent
W.mkdir(parents=True, exist_ok=True)
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
cfg = read(P / 'Content/ColdSteelData/player_body.json')
female = cfg['body_variants']['kaitlin']
prefixes = ('Warhammer.', 'Melee.', 'Bow.', 'Staff.', 'Kukri.', 'Rifle.', 'Pistol.', 'SinglePistol.', 'DualPistol.')
plan = {}
for role, source in cfg['clips'].items():
    if not role.startswith(prefixes):
        continue
    target = female['clips'].get(role)
    key = hashlib.sha256((source + '|' + str(target)).encode()).hexdigest()[:16]
    plan.setdefault(key, {'source': source, 'target': target, 'roles': []})['roles'].append(role)
if (W / 'plan.json').exists():
    plan = read(W / 'plan.json')
else:
    (W / 'plan.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
names = ['root', 'pelvis', 'spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05']
for side in ('l', 'r'):
    names += [f'{b}_{side}' for b in ('clavicle', 'upperarm', 'lowerarm', 'hand')]
    names += [f'{d}_{j:02}_{side}' for d in ('thumb', 'index', 'middle', 'ring', 'pinky') for j in range(1, 4)]
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
started = time.monotonic()
written = 0
for key, spec in plan.items():
    out = W / 'Captured' / (key + '.json')
    if out.exists():
        continue
    result = dict(spec, samples={})
    for variant in ('source', 'target'):
        path = spec[variant]
        if not path:
            result['samples'][variant] = None
            continue
        if path.split('.')[0] in dirty:
            raise RuntimeError('Unsaved source animation: ' + path)
        clip = u.load_asset(path)
        model = clip.get_editor_property('data_model_interface')
        rate = model.get_frame_rate()
        count = model.get_number_of_keys()
        seconds = (count - 1) * rate.denominator / rate.numerator
        frames = []
        for fraction in (0., .25, .5, .75, 1.):
            poses = u.AnimationLibrary.get_bone_poses_for_time(clip, names, fraction * seconds, False)
            frames.append([[t.translation.x, t.translation.y, t.translation.z,
                            t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w,
                            t.scale3d.x, t.scale3d.y, t.scale3d.z] for t in poses])
        result['samples'][variant] = {'names': names, 'frames': frames, 'keys': count,
                                      'rate': [rate.numerator, rate.denominator],
                                      'markers': [str(m.marker_name) for m in u.AnimationLibrary.get_animation_sync_markers(clip)]}
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
    written += 1
    if time.monotonic() - started > 40:
        break
remaining = sum(not (W / 'Captured' / (k + '.json')).exists() for k in plan)
print('WEAPON_CONTACT_CAPTURE', written, 'remaining', remaining)
