"""Blender (background): foregrip pose layers for the M870 loader clips.

Same method and inputs as M870CommonFurniture20261016/author_profiles.py (the
installed DA_M870_<family> layers): while the left hand holds the pump (within
2-7 mm of the idle hold, relative to WPN_bolt) the accepted common grasp replaces
the pump grasp; the fetch / dock / push / flick, where the hand is away, are left
as authored. Writes Profiles/<family>.json with entries for the 14 loader clips.
"""
import bpy, json, math, sys, gzip, ast
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
O = Path(__file__).parent; S = O.parent; F = S / 'M870CommonFurniture20261016'; X = O / 'Profiles'; X.mkdir(exist_ok=True)
sys.path.insert(0, str(S / 'RSH12Grip20261003'))
from pose_geometry import matrix
bpy.ops.wm.open_mainfile(filepath=str(S / 'M870LeftArm20261016/M870_LeftArm_Editable.blend'))
rig = bpy.data.objects['SK_Super90']; rig.animation_data_clear(); rig.data.pose_position = 'POSE'
with gzip.open(F / 'Inputs/native_geometry.json.gz', 'rt') as f: D = json.load(f)
M = json.loads((S / 'Super90Foregrips20261007/models.json').read_text())
M['mount_native'] = json.loads((F / 'models.json').read_text())['foregrip_mount_blender']
donors = json.loads((S / 'M16UniversalAttachments20260920/authoring.json').read_text())['donors']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}; names = list(rest)
parents = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
C = Matrix.Diagonal((100, -100, 100, 1)); Ci = C.inverted()
K = {n: (C @ rest[n]).inverted() @ matrix(D['rest'][n]) for n in names}
Ki = {n: k.inverted() for n, k in K.items()}
mount = Matrix(M['mount_native']); root_rest_inv = rest['WPN_bolt'].inverted()
CL = json.loads((O / 'clips.json').read_text()); IN = json.loads((O / 'inputs.json').read_text())
ROOT = '/Game/Weapons/M870/Speedloader20261016/Animations/A_M870_loader_'
D['clips'] = {'idle': {'asset': '', 'duration': 0, 'samples': [{'time': 0., 'local': IN['m870_clips']['idle']['rows'][0]}]}}
for role, clip in CL.items():
    D['clips'][role] = {'asset': ROOT + role, 'duration': clip['frames'] / 60.,
                        'samples': [{'time': i / 60., 'local': r} for i, r in enumerate(clip['rows'])]}
finger_names = [n for n in names if n.endswith('_l') and n.startswith(('thumb', 'index', 'middle', 'ring', 'pinky'))]
changed = ['clavicle_l', 'upperarm_l', 'lowerarm_l', 'lowerarm_aux_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l', 'hand_l'] + finger_names


def frame(data, n):
    p = data[n].translation
    if n == 'hand_l': end = data['middle_01_l'].translation
    elif '_metacarpal_' in n: end = data[n.split('_')[0] + '_01_l'].translation
    elif '_03_' in n: end = p + (p - data[n.replace('_03_', '_02_')].translation)
    else: end = data[n.replace('_02_', '_03_') if '_02_' in n else n.replace('_01_', '_02_')].translation
    x = (end - p).normalized(); wide = data['index_01_l'].translation - data['pinky_01_l'].translation
    forward = data['middle_01_l'].translation - data['hand_l'].translation
    z = forward.cross(wide).normalized(); y = z.cross(x).normalized(); z = x.cross(y).normalized()
    m = Matrix((x, y, z)).transposed().to_4x4(); m.translation = p; return m


anatomy = {n: frame(rest, n) for n in ['hand_l'] + finger_names}


def native(sample):
    world = {}
    for n, v in sample['local'].items(): world[n] = world.get(D['parents'][n], Matrix.Identity(4)) @ matrix(v)
    return {n: Ci @ world[n] @ Ki[n] for n in names}, world


def carry(old, hand):
    p = {n: m.copy() for n, m in old.items()}; shoulder = old['upperarm_l'].translation.copy(); elbow = old['lowerarm_l'].translation.copy(); wrist = old['hand_l'].translation.copy()
    goal = hand.translation; v = goal - shoulder; length = v.length; axis = v.normalized(); a = (elbow - shoulder).length; b = (wrist - elbow).length
    reach = (a + b) * .985
    if length > reach:
        shift = axis * (length - reach); shoulder += shift; p['clavicle_l'].translation += shift; length = reach
    length = max(abs(a - b) + 1e-6, length); along = (a * a - b * b + length * length) / (2 * length)
    pole = elbow - old['upperarm_l'].translation; pole -= axis * pole.dot(axis)
    knee = shoulder + axis * along + pole.normalized() * math.sqrt(max(0, a * a - along * along))
    qa = (elbow - old['upperarm_l'].translation).rotation_difference(knee - shoulder)
    qb = (wrist - elbow).rotation_difference(goal - knee)
    p['upperarm_l'] = Matrix.LocRotScale(shoulder, qa @ old['upperarm_l'].to_quaternion(), Vector((1, 1, 1)))
    p['lowerarm_l'] = Matrix.LocRotScale(knee, qb @ old['lowerarm_l'].to_quaternion(), Vector((1, 1, 1)))
    axis = (goal - knee).normalized(); roll = hand.to_quaternion() @ (qb @ old['hand_l'].to_quaternion()).inverted()
    along = Vector((roll.x, roll.y, roll.z)).dot(axis); angle = 2 * math.atan2(along, roll.w)
    angle = (angle + math.pi) % (2 * math.pi) - math.pi
    for n, w in (('lowerarm_aux_l', .20), ('lowerarm_twist_02_l', .50), ('lowerarm_twist_01_l', .80)):
        base = p['lowerarm_l'] @ old['lowerarm_l'].inverted() @ old[n]
        p[n] = Matrix.LocRotScale(base.translation, Quaternion(axis, angle * w) @ base.to_quaternion(), Vector((1, 1, 1)))
    p['hand_l'] = hand; return p


d = json.loads((S / 'M870LeftArm20261016/before_diagnosis.json').read_text())
ru = rest['lowerarm_l'].translation - rest['upperarm_l'].translation; rf = rest['hand_l'].translation - rest['lowerarm_l'].translation
PROXIMAL_FRACTION = 0.; ELBOW_BLEND = 1.; HINGE_ROLL = 0.
tree = ast.parse((S / 'M870LeftArm20261016/author_left_arm.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('basis', 'ease', 'frames', 'solve')], type_ignores=[]), '<native M870 stations>', 'exec'))
FU = basis(ru, Vector(d['native_hinge']['upper'])); FF = basis(rf, Vector(d['native_hinge']['fore']))
idle_source, _ = native(D['clips']['idle']['samples'][0]); hold_local = idle_source['WPN_bolt'].inverted() @ idle_source['hand_l']
report = {'source': 'M870CommonFurniture20261016/author_profiles.py method', 'changed_bones': changed, 'families': {}, 'runtime_tested': False}
for family in ('vertical', 'canted', 'prism', 'angled'):
    donor = donors[family]; dr = {n: Matrix(v) for n, v in donor['rest'].items()}; dp = {n: Matrix(v) for n, v in donor['pose'].items()}
    da = {n: frame(dr, n) for n in ['hand_l'] + finger_names}; posed = {n: dp[n] @ dr[n].inverted() @ da[n] for n in da}
    hand = Matrix(M['parts'][family]['hand_in_mount']) @ dr['hand_l'].inverted() @ da['hand_l'] @ anatomy['hand_l'].inverted() @ rest['hand_l']
    grasp = {'hand_l': hand}; finger_local = {}
    for n in finger_names:
        par = parents[n]
        donor_bind = da[par].to_quaternion().inverted() @ da[n].to_quaternion()
        donor_pose = posed[par].to_quaternion().inverted() @ posed[n].to_quaternion()
        delta = donor_bind.inverted() @ donor_pose
        target_bind = anatomy[par].to_quaternion().inverted() @ anatomy[n].to_quaternion()
        parent_anatomy = grasp[par] @ rest[par].inverted() @ anatomy[par]
        q = parent_anatomy.to_quaternion() @ target_bind @ delta @ anatomy[n].to_quaternion().inverted() @ rest[n].to_quaternion()
        pos = grasp[par] @ (rest[par].inverted() @ rest[n]).translation
        grasp[n] = Matrix.LocRotScale(pos, q, Vector((1, 1, 1))); finger_local[n] = grasp[par].to_quaternion().inverted() @ q
    anchors = ('index_02_l', 'middle_02_l', 'ring_02_l', 'thumb_02_l')
    donor_mount_inv = Matrix(donor['mount']).inverted(); lift = Vector((0, 0, M['parts'][family]['body_lift']))
    shift = sum(((donor_mount_inv @ dp[n]).translation + lift - grasp[n].translation for n in anchors), Vector()) / len(anchors)
    hand.translation += shift
    result = {'family': family, 'clips': []}
    for kind, clip in D['clips'].items():
        if kind == 'idle': continue
        tracks = {n: [] for n in changed}; times = []
        for sample in clip['samples']:
            old, world = native(sample)
            contact = (old['WPN_bolt'].inverted() @ old['hand_l']).translation
            release = max(0., min(1., ((contact - hold_local.translation).length - .02) / .05))
            contact_weight = 1. - release * release * (3. - 2. * release)
            target = old['WPN_bolt'] @ root_rest_inv @ mount @ hand; p = carry(old, target)
            for n in finger_names:
                par = parents[n]; lp = old[par].inverted() @ old[n]
                p[n] = p[par] @ Matrix.LocRotScale(lp.translation, finger_local[n], lp.to_scale())
            p = solve(p, frames(p)[2])
            new_world = {n: C @ p[n] @ K[n] for n in names}
            times.append(sample['time'])
            for n in changed:
                par = parents[n]; local = new_world[par].inverted() @ new_world[n]; base = matrix(sample['local'][n])
                q = Quaternion().slerp(local.to_quaternion() @ base.to_quaternion().inverted(), contact_weight)
                if tracks[n]:
                    previous = Quaternion((tracks[n][-1][6], *tracks[n][-1][3:6]))
                    if q.dot(previous) < 0: q.negate()
                elif q.w < 0: q.negate()
                delta = (local.translation - base.translation) * contact_weight if n == 'clavicle_l' else Vector()
                tracks[n].append([*delta, q.x, q.y, q.z, q.w, 0., 0., 0.])
        entry = {'kind': kind, 'base': clip['asset'], 'duration': clip['duration'], 'tracks': []}
        for n, values in tracks.items():
            zero = [0, 0, 0, 0, 0, 0, 1, 0, 0, 0]
            if all(max(abs(a - b) for a, b in zip(zero, v)) < 1e-6 for v in values): continue
            constant = all(max(abs(a - b) for a, b in zip(values[0], v)) < 1e-6 for v in values[1:])
            entry['tracks'].append({'bone': n, 'times': [0.] if constant else times, 'values': values[0] if constant else [x for v in values for x in v]})
        result['clips'].append(entry)
        print('M870_LOADER_GRIP_LAYER', family, kind, flush=True)
    (X / (family + '.json')).write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
    report['families'][family] = {'group_grasp_shift_m': list(shift), 'clips': len(result['clips'])}
(O / 'profile_authoring.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('M870_LOADER_GRIP_PROFILES_AUTHORED', flush=True)
