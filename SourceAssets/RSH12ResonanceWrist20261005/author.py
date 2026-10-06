"""Re-author only the RSH Resonance profile and its editable source; no renders."""
import bpy, copy, json, shutil, sys
from pathlib import Path
from mathutils import Matrix, Quaternion

O = Path(__file__).parent
S = O.parent
CURRENT = S/'RSH12Foregrips20261004/Profiles'
BEFORE = O/'Before'
BEFORE.mkdir(exist_ok=True)
for name in ('angled.json', 'RSH12_angled_Editable.blend'):
    if not (BEFORE/name).exists():
        shutil.copy2(CURRENT/name, BEFORE/name)
sys.path.insert(0, str(S/'RSH12InspectGrip20261004'))
sys.path.insert(0, str(O))
from grip_scene import load, pose, matrix, applied, track_at, set_pose
from arm_support import support_arm, contact_weight, WRIST_SWING_DEGREES
sys.path.insert(0, str(S/'RSH12InspectArmRepair20261005'))
from inspect_support import rewrite_inspect

rig, data, _, meta = load()
source = json.loads((BEFORE/'angled.json').read_text())
result = copy.deepcopy(source)
rest = {bone.name: bone.matrix_local.copy() for bone in rig.data.bones}
reflect = Matrix.Diagonal((1, -1, 1, 1))
to_ue = (rig.matrix_world.inverted() @ reflect @ Matrix.Diagonal((.01, .01, .01, 1))).inverted()
changed_names = ['clavicle_l','upperarm_l','lowerarm_l','hand_l'] + [
    n for n in rest if n.endswith('_l') and n.startswith(('upperarm_twist','lowerarm_twist'))]
receipt = {'revision':'rsh12-resonance-wrist-20261005', 'family':'angled',
           'wrist_swing_design_degrees':WRIST_SWING_DEGREES, 'clips':[],
           'runtime_tested':False, 'rendered':False}
for entry in result['clips']:
    kind = entry['kind']
    original_entry = next(row for row in source['clips'] if row['kind'] == kind)
    existing = {track['bone']: track for track in original_entry['tracks']}
    tracks = {name: [] for name in changed_names}
    times = []
    previous = {}
    for sample in data['clips'][kind]['samples']:
        time = sample['time']
        times.append(time)
        weight = contact_weight(kind, time, entry['duration'])
        p = pose(rig, data, source, kind, sample)
        support_arm(p, rest, weight)
        local = applied({n:matrix(v) for n,v in sample['local'].items()}, original_entry, time)
        world = {n:to_ue@m@reflect for n,m in p.items()}
        for name in changed_names:
            if weight <= 0.0:
                value = track_at(existing[name], time) if name in existing else [0,0,0,0,0,0,1,0,0,0]
            else:
                parent = data['parents'][name]
                authored_local = world[parent].inverted() @ world[name]
                translation, rotation, _ = authored_local.decompose()
                base_translation, base_rotation, base_scale = matrix(sample['local'][name]).decompose()
                if name != 'clavicle_l':
                    translation = local[name].translation
                delta = rotation @ base_rotation.inverted()
                value = [*(translation-base_translation), delta.x,delta.y,delta.z,delta.w,
                         *(local[name].to_scale()-base_scale)]
            q = Quaternion((value[6], *value[3:6]))
            if name in previous and previous[name].dot(q) < 0:
                q.negate()
                value[3:7] = [q.x,q.y,q.z,q.w]
            previous[name] = q
            tracks[name].append(value)
    updated = {track['bone']:track for track in entry['tracks']}
    for name, values in tracks.items():
        updated[name] = {'bone':name, 'times':times, 'values':[v for key in values for v in key]}
    entry['tracks'] = list(updated.values())
    receipt['clips'].append({'kind':kind, 'duration':entry['duration'], 'samples':len(times)})
    print('RSH_RESONANCE_ARM_AUTHORED', kind, flush=True)

rewrite_inspect(rig, data, result)
payload = json.dumps(result, separators=(',',':'))
(O/'profile.json').write_text(payload, encoding='utf8')
(CURRENT/'angled.json').write_text(payload, encoding='utf8')
set_pose(rig, pose(rig,data,result,'idle',data['clips']['idle']['samples'][0]))
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'RSH12_ResonanceWrist_Editable.blend'))
shutil.copy2(O/'RSH12_ResonanceWrist_Editable.blend', CURRENT/'RSH12_angled_Editable.blend')
(O/'authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
print('RSH_RESONANCE_ARM_AUTHORING_SAVED', flush=True)
