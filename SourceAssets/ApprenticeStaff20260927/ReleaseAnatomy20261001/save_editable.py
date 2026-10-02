"""Save native-rig, complete editable charge-to-release takes in Blender.

The .80 second authored take uses the same six-key weights and anatomical
lower-arm scalar interpolation as runtime. No rendering or game is launched.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).resolve().parent
data = json.loads((P / 'full-pose.json').read_text(encoding='utf-8-sig'))
bpy.ops.wm.open_mainfile(filepath=str(P.parent / 'ChargeFlow20261001/Staff_ChargeFlow20261001.blend'))
bpy.context.preferences.filepaths.save_version = 0
rig = bpy.data.objects['Staff_ChargeFlow20261001']
rig.name = 'Staff_ReleaseAnatomy20261001'
rig['source'] = 'ReleaseAnatomy20261001/full-pose.json'
rig['revision'] = data['revision']
rig['contact_contract'] = data['contact_contract']
scene = bpy.context.scene
FPS, DURATION = 120, .80
scene.render.fps = FPS
parents = dict(data['parent'], staff_grip='hand_r')
names = list(data['order']) + ['staff_grip']
rest = {n: Matrix(m) for n, m in data['rest'].items()}
mirror = Matrix.Diagonal((1, -1, 1))


def convert(m):
    result = (mirror @ m.to_3x3() @ mirror).to_4x4()
    result.translation = mirror @ m.translation * .01
    return result


def mix(a, b, u):
    # UE FTransform::Blend uses shortest-path normalized quaternion lerp.
    qa, qb = a.to_quaternion(), b.to_quaternion()
    if qa.dot(qb) < 0:
        qb.negate()
    q = qa * (1. - u) + qb * u
    q.normalize()
    result = q.to_matrix().to_4x4()
    result.translation = a.translation.lerp(b.translation, u)
    return result


def ease(t):
    t = min(1., max(0., t))
    return t*t*t*(t*(t*6.-15.)+10.)


def weights(age):
    w = [0.] * 6
    if age < .035:
        u = ease(age / .035)
        w[1], w[2] = 1. - u, u
    elif age < .18:
        u = ease((age - .035) / (.18 - .035))
        w[2], w[3] = 1. - u, u
    elif age < .28:
        u = ease((age - .18) / (.28 - .18))
        w[3], w[4] = 1. - u, u
    elif age < .38:
        w[4] = 1.
    else:
        u = ease((age - .38) / .42)
        w[4], w[0] = 1. - u, u
    return w


def sample(variant, age):
    clips, w = data['poses'][variant], weights(age)
    world = {n: m.copy() for n, m in rest.items()}
    for n in data['order']:
        if n == 'lowerarm_r':
            entry, entry_total = None, 0.
            for k in (0, 5):
                if w[k] <= 0.:
                    continue
                m = Matrix(clips[k]['local'][n])
                entry = m if entry is None else mix(entry, m, w[k] / (entry_total + w[k]))
                entry_total += w[k]
            active_total = sum(w[1:5])
            if active_total > 0.:
                flexion = sum(w[k] * clips[k]['elbow_flexion_offset_radians'] for k in range(1, 5)) / active_total
                roll = sum(w[k] * clips[k]['forearm_roll_radians'] for k in range(1, 5)) / active_total
                contract = data['elbow_contract']
                rotation = Quaternion(Vector(contract['hinge_upper_local']), flexion) * Matrix(contract['lower_rest_rotation']).to_quaternion() * Quaternion(Vector(contract['forearm_axis_lower_local']), roll)
                result = rotation.to_matrix().to_4x4()
                result.translation = Matrix(clips[1]['local'][n]).translation
                if entry is not None:
                    result = mix(entry, result, active_total / (entry_total + active_total))
            else:
                result = entry
        else:
            result, total = None, 0.
            for clip, weight in zip(clips, w):
                if weight <= 0.:
                    continue
                m = Matrix(clip['local'][n])
                result = m if result is None else mix(result, m, weight / (total + weight))
                total += weight
        world[n] = world[parents[n]] @ result
    world['staff_grip'] = world['hand_r'] @ Matrix(data['variants'][variant]['hand']).inverted()
    return world


def key_frame(frame, world, previous):
    converted = {n: convert(m) for n, m in world.items()}
    for n in names:
        bone = rig.pose.bones[n]
        parent = parents[n]
        relative = converted[parent].inverted() @ converted[n] if parent else converted[n]
        ref = rig.data.bones[n].matrix_local
        if parent:
            ref = rig.data.bones[parent].matrix_local.inverted() @ ref
        bone.rotation_mode = 'QUATERNION'
        bone.matrix_basis = ref.inverted() @ relative
        if n in previous and bone.rotation_quaternion.dot(previous[n]) < 0:
            bone.rotation_quaternion.negate()
        previous[n] = bone.rotation_quaternion.copy()
        for field in ('location', 'rotation_quaternion', 'scale'):
            bone.keyframe_insert(field, frame=frame)


actions = []
for variant in data['poses']:
    action = bpy.data.actions.new('A_Staff_ReleaseAnatomy20261001_' + variant)
    action.use_fake_user = True
    action['source'] = 'ReleaseAnatomy20261001/full-pose.json'
    action['entry'] = 'Exact current charge RaisedSettled; recover to preserved native idle'
    action['duration_seconds'] = DURATION
    rig.animation_data.action = action
    previous = {}
    frames = sorted(set([float(i) for i in range(97)] + [t*FPS for t in (.035, .18, .28, .38, .80)]))
    for frame in frames:
        key_frame(frame, sample(variant, frame/FPS), previous)
    for layer in action.layers:
        for strip in layer.strips:
            for slot in action.slots:
                channelbag = strip.channelbag(slot)
                if channelbag:
                    for curve in channelbag.fcurves:
                        for key in curve.keyframe_points:
                            key.interpolation = 'LINEAR'
    actions.append(action.name)
    print('SAVED_RELEASE_ANATOMY_TAKE', action.name, len(frames), flush=True)

rig.animation_data.action = bpy.data.actions[actions[0]]
if len(rig.animation_data.action.slots):
    rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_start, scene.frame_end = 0, 96
scene.timeline_markers.clear()
for name, age in [('Raised_exact_charge', 0.), ('Windup', .035), ('Release', .18), ('Follow', .28), ('Recover_start', .38), ('Idle', .80)]:
    scene.timeline_markers.new(name, frame=round(age * FPS))
scene.frame_set(0)
output = P / 'Staff_ReleaseAnatomy20261001.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output))
(P / 'editable-source.json').write_text(json.dumps(dict(source=output.name, actions=actions,
    revision=data['revision'], source_input='../ChargeFlow20261001/Staff_ChargeFlow20261001.blend',
    fps=FPS, duration_seconds=DURATION, frame_start=0, frame_end=96,
    key_times_seconds=[0., .035, .18, .28, .38, .80],
    runtime='StaffCastMotion::Swing/Hold/Recover; complete local right chain and lowerarm hinge/pronation scalars',
    reference_take_interpolation='120 Hz shortest-path normalized local quaternion lerp; elbow flexion/pronation mixed as scalars; entry blended once',
    shaft_driver='Whole-arm FK followed by inverse hand-in-grip; no separate hand pivot',
    ue_import_required=False, rendered=False, runtime_tested=False), indent=2) + '\n', encoding='utf-8')
print('STAFF_RELEASE_ANATOMY_EDITABLE_SAVED', str(output), flush=True)
