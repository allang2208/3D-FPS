"""Save four complete editable V7 charge takes in background Blender.

The take starts at the default stationary carry and preserves the 0.95 second
authoring clock. Game integration captures its actual entry and owns timing.
No rendering, test, UE launch or UE asset import is performed.
"""
import json
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).resolve().parent
data = json.loads((P/'full-pose.json').read_text(encoding='utf-8-sig'))
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'CastElbowRepair20260930/Staff_CastElbow20260930.blend'))
bpy.context.preferences.filepaths.save_version = 0
rig = bpy.data.objects['Staff_CastElbow20260930']
rig.name = 'Staff_ChargeFlow20261001'
rig['source'] = 'ChargeFlow20261001/full-pose.json'
rig['revision'] = data['revision']
rig['runtime_endpoint'] = 'Current Raised: contact (49,26,-8) camera cm, all offsets included once'
scene = bpy.context.scene
FPS, DURATION = 120, .95
scene.render.fps = FPS
parents = dict(data['parent'], staff_grip='hand_r')
names = list(data['order'])+['staff_grip']
rest = {n:Matrix(m) for n,m in data['rest'].items()}
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
    q = qa*(1.-u)+qb*u
    q.normalize()
    m = q.to_matrix().to_4x4()
    m.translation = a.translation.lerp(b.translation, u)
    return m


def weights(phase):
    t = max(0., min(1., phase))
    if t >= 1.:
        return [0., 0., 0., 0., 0., 1.]
    u = t*t*(3.-2.*t)
    knots = [0., 0., 0., 0., .40, .72, 1., 1., 1., 1.]
    basis = [float(knots[i] <= u < knots[i+1]) for i in range(9)]
    for degree in range(1, 4):
        for i in range(9-degree):
            a = knots[i+degree]-knots[i]
            b = knots[i+degree+1]-knots[i+1]
            basis[i] = ((u-knots[i])/a*basis[i] if a > 0. else 0.) + (
                (knots[i+degree+1]-u)/b*basis[i+1] if b > 0. else 0.)
    return basis[:6]


def sample(variant, phase):
    clips = [data['default_entry'][variant], *data['poses'][variant]]
    w = weights(phase)
    # Same positive weights and stable local quaternion fold as StaffChargeFlow
    # and StaffGripPose. The controls form one continuous sweep, not five stops.
    world = {n:m.copy() for n,m in rest.items()}
    for n in data['order']:
        result, accumulated = None, 0.
        for clip, weight in zip(clips, w):
            if weight <= 0.:
                continue
            local = Matrix(clip['local'][n])
            result = local if result is None else mix(result, local, weight/(accumulated+weight))
            accumulated += weight
        if n == 'lowerarm_r' and sum(w[1:]) > 0.:
            total = sum(w[1:])
            flexion = sum(weight*clip['elbow_flexion_offset_radians'] for weight,clip in zip(w[1:],clips[1:]))/total
            roll = sum(weight*clip['forearm_roll_radians'] for weight,clip in zip(w[1:],clips[1:]))/total
            contract = data['elbow_contract']
            rotation = Quaternion(Vector(contract['hinge_upper_local']), flexion) * Matrix(contract['lower_rest_rotation']).to_quaternion() * Quaternion(Vector(contract['forearm_axis_lower_local']), roll)
            charged = rotation.to_matrix().to_4x4()
            charged.translation = Matrix(clips[1]['local'][n]).translation
            result = mix(Matrix(clips[0]['local'][n]), charged, total/(total+w[0])) if w[0] > 0. else charged
        world[n] = world[parents[n]] @ result
    world['staff_grip'] = world['hand_r'] @ Matrix(data['variants'][variant]['hand']).inverted()
    return world


def key_frame(frame, world, previous):
    converted = {n:convert(m) for n,m in world.items()}
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
    action = bpy.data.actions.new('A_Staff_ChargeFlow20261001_'+variant)
    action.use_fake_user = True
    action['source'] = 'ChargeFlow20261001/full-pose.json'
    action['entry'] = 'Default stationary carry; game captures actual pose and gait'
    action['charge_duration_seconds'] = DURATION
    rig.animation_data.action = action
    previous = {}
    frames = sorted(set([float(i) for i in range(115)]+[t*FPS*DURATION for t in data['phase_normalized']]))
    for frame in frames:
        key_frame(frame, sample(variant, frame/(FPS*DURATION)), previous)
    for layer in action.layers:
        for strip in layer.strips:
            for slot in action.slots:
                channelbag = strip.channelbag(slot)
                if channelbag:
                    for curve in channelbag.fcurves:
                        for key in curve.keyframe_points:
                            key.interpolation = 'LINEAR'
    actions.append(action.name)
    print('SAVED_CHARGE_FLOW_TAKE', action.name, len(frames), flush=True)

rig.animation_data.action = bpy.data.actions[actions[0]]
if len(rig.animation_data.action.slots):
    rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_start, scene.frame_end = 0, 114
scene.timeline_markers.clear()
scene.timeline_markers.new('Captured_carry_reference', frame=0)
for name, phase in zip(data['key_names'], data['phase_normalized']):
    scene.timeline_markers.new(name, frame=round(phase*FPS*DURATION))
scene.frame_set(0)
output = P/'Staff_ChargeFlow20261001.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output))
(P/'editable-source.json').write_text(json.dumps(dict(source=output.name, actions=actions,
    revision=data['revision'],
    source_input='../CastElbowRepair20260930/Staff_CastElbow20260930.blend',
    fps=FPS, duration_seconds=DURATION, authored_key_phase=data['phase_normalized'],
    runtime='StaffChargeFlow: full local right-chain table, captured entry and shared skill clock',
    reference_take_interpolation='120 Hz local quaternion fold of the same clamped cubic B-spline as runtime',
    control_knots=[0, 0, 0, 0, .40, .72, 1, 1, 1, 1], parameter_ease='t*t*(3-2*t)',
    elbow_interpolation=data['elbow_contract']['runtime_interpolation'],
    ue_import_required=False, rendered=False, runtime_tested=False), indent=2)+'\n', encoding='utf-8')
print('STAFF_CHARGE_FLOW_EDITABLE_SAVED', str(output), flush=True)
