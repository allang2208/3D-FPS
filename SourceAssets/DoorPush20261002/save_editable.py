"""Save increased whole-arm guard sway and live recovery in background.

No render, engine, import, or runtime test. The right fist stays at the
existing unarmed idle example; runtime leaves the weapon right arm alone.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
data = json.loads((P / 'full-pose.json').read_text(encoding='utf-8'))
base = ROOT / 'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/M4_BareArmsV7.blend'
bpy.ops.wm.open_mainfile(filepath=str(base))
bpy.context.preferences.filepaths.save_version = 0
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE'
           and all(n in o.data.bones for n in ('clavicle_l', 'clavicle_r', 'hand_l', 'hand_r')))
rig.name = 'DoorPush_LeftFist_V7_20261002'
rig['runtime_table'] = 'DoorPushAuthored20261002.h'
rig['revision'] = data['revision']
rig['entry_contract'] = data['entry_contract']
rig['recovery_contract'] = data['recovery_contract']
rig['guard_sway_contract'] = data['guard_sway']['method']
rig.animation_data_clear()
rig.animation_data_create()
scene = bpy.context.scene
FPS = 1000  # Preserve entry, hold sway key clocks and recovery endpoints.
scene.render.fps = FPS
mirror = Matrix.Diagonal((1., -1., 1.))


def convert(m):
    result = (mirror @ m.to_3x3() @ mirror).to_4x4()
    result.translation = mirror @ m.translation * .01
    return result


def ease(x):
    x = min(1., max(0., x))
    return x*x*x*(x*(x*6.-15.)+10.)


def segment_blend(segment, x):
    x = min(1., max(0., x))
    return ease(x)


def sample(age, name):
    a = max(0, min(len(data['times']) - 2,
                   next((i - 1 for i, t in enumerate(data['times']) if i > 0 and age <= t), len(data['times']) - 2)))
    b = a + 1
    alpha = segment_blend(a, (age - data['times'][a]) / (data['times'][b] - data['times'][a]))
    ka, kb = data['poses'][a], data['poses'][b]
    ma, mb = Matrix(ka['local'][name]), Matrix(kb['local'][name])
    q = ma.to_quaternion().slerp(mb.to_quaternion(), alpha)
    if name == 'lowerarm_l' and data['lower_uses_native_joint_scalars']:
        ja, jb = ka['anatomy'], kb['anatomy']
        flex = ja['elbow_flexion_offset_radians'] * (1. - alpha) + jb['elbow_flexion_offset_radians'] * alpha
        roll = ja['forearm_roll_radians'] * (1. - alpha) + jb['forearm_roll_radians'] * alpha
        j = data['joint_definition']
        q = (Quaternion(Vector(j['elbow_hinge']), flex)
             @ Matrix(j['lower_rest_rotation']).to_quaternion()
             @ Quaternion(Vector(j['forearm_axis']), roll))
        q.normalize()
    result = q.to_matrix().to_4x4()
    result.translation = ma.translation.lerp(mb.translation, alpha)
    return result


action = bpy.data.actions.new('A_DoorPush_LeftFist_V7_20261002_GuardV10Sway250msRecover')
action.use_fake_user = True
action['revision'] = data['revision']
action['source'] = 'SourceAssets/DoorPush20261002/full-pose.json'
action['duration_seconds'] = data['duration_seconds']
action['door_contact_seconds'] = data['contact_seconds']
action['prepare_hold_seconds'] = data['hold_seconds']
action['push_start_seconds'] = data['push_start_seconds']
action['fist_source'] = data['fist_source']
action['fist_transfer'] = data['full_action_transfer']
action['fist_acceptance'] = data['fist_acceptance']
action['contact_brake_seconds'] = data['contact_brake_seconds']
action['rebound_seconds'] = data['rebound_seconds']
action['uses_forward_push'] = False
action['uses_contact_brake'] = False
action['uses_short_rebound'] = False
action['guard_pose_source'] = data['guard_pose_source']
action['recover_start_seconds'] = data['recover_start_seconds']
action['guard_sway_method'] = data['guard_sway']['method']
action['guard_sway_side_max_cm'] = data['guard_sway']['side_max_cm']
action['guard_sway_up_max_cm'] = data['guard_sway']['up_max_cm']
action['guard_sway_forward_max_cm'] = data['guard_sway']['forward_max_cm']
action['guard_sway_child_locals_unchanged'] = True
action['runtime_interpolation'] = data['lowerarm_interpolation'] + '; ' + data['other_bone_interpolation']
action['reference_url'] = data['reference_url']
action['reference_photo'] = data['reference_photo']
action['reference_interpretation'] = data['reference_interpretation']
rig.animation_data.action = action
end = round(data['duration_seconds'] * FPS)
previous = {}
base_world = {n: Matrix(m) for n, m in data['example_base_component'].items()}
for frame in range(end + 1):
    age = frame / FPS
    for name in data['all_order']:
        if name in data['order']:
            relative = sample(age, name)
        else:
            parent = data['parent'][name]
            relative = base_world[parent].inverted() @ base_world[name]
        bone = rig.pose.bones[name]
        ref = rig.data.bones[name].matrix_local
        if bone.parent:
            ref = rig.data.bones[bone.parent.name].matrix_local.inverted() @ ref
        bone.rotation_mode = 'QUATERNION'
        bone.matrix_basis = ref.inverted() @ convert(relative)
        if name in previous and bone.rotation_quaternion.dot(previous[name]) < 0:
            bone.rotation_quaternion.negate()
        previous[name] = bone.rotation_quaternion.copy()
        for prop in ('location', 'rotation_quaternion', 'scale'):
            bone.keyframe_insert(prop, frame=frame)
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for key in curve.keyframe_points:
                    key.interpolation = 'LINEAR'
action.use_frame_range = True
action.frame_start, action.frame_end = 0., float(end)
scene.frame_start, scene.frame_end = 0, end
scene.timeline_markers.clear()
for name, age in zip(data['key_names'], data['times']):
    scene.timeline_markers.new(name, frame=round(age * FPS))
scene.frame_set(round(data['prepare_seconds'] * FPS))
output = P / 'DoorPush_LeftFist_V7_20261002.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output))
(P / 'editable-source.json').write_text(json.dumps(dict(
    revision=data['revision'], source=output.name, take=action.name,
    input=base.relative_to(ROOT).as_posix(), fps=FPS, frames_including_endpoint=end + 1,
    duration_seconds=data['duration_seconds'], contact_seconds=data['contact_seconds'],
    prepare_hold_seconds=data['hold_seconds'], push_start_seconds=data['push_start_seconds'],
    contact_brake_seconds=data['contact_brake_seconds'], rebound_seconds=data['rebound_seconds'],
    uses_forward_push=False, uses_contact_brake=False, uses_short_rebound=False,
    guard_pose_source=data['guard_pose_source'], guard_pose_source_revision=data['guard_pose_source_revision'],
    guard_sway=data['guard_sway'],
    recover_start_seconds=data['recover_start_seconds'], recovery_seconds=data['recovery_seconds'],
    fist_source=data['fist_source'], fist_source_json=data['fist_source_json'],
    fist_transfer=data['full_action_transfer'],
    reference_photo=data['reference_photo'], photo_guard=data['photo_guard'],
    fist_acceptance=data['fist_acceptance'],
    runtime_table='Source/FPSGAME/Movement/DoorPushAuthored20261002.h',
    interpolation=action['runtime_interpolation'], authored_skin='Accepted BarePalmV7/M4; native bind and skin retained',
    runtime_entry_and_recovery='Current loaded weapon or unarmed live left chain; Blender shows an unarmed example',
    rendered=False, runtime_tested=False, ue_asset_import_required=False), indent=2) + '\n', encoding='utf-8')
(P / 'authored-source-completion.json').write_text(json.dumps(dict(
    status='guard_v10_increased_rigid_whole_arm_sway_250ms_hold_direct_recovery_actual_editable_blend_saved',
    revision=data['revision'], header='Source/FPSGAME/Movement/DoorPushAuthored20261002.h',
    editable_source=output.relative_to(ROOT).as_posix(), take=action.name,
    backup='SourceAssets/DoorPush20261002/FeedbackAllWeaponsV10_20261002/BeforeAuthored',
    source=data['source'], source_revision=data['source_revision'],
    source_keys=data['source_keys'], full_action_transfer=data['full_action_transfer'],
    reference_photo=data['reference_photo'], photo_guard=data['photo_guard'],
    guard_pose_source=data['guard_pose_source'], guard_pose_source_revision=data['guard_pose_source_revision'],
    guard_sway=data['guard_sway'],
    native_pose_bones=len(data['order']), keys=len(data['poses']),
    lower_uses_native_joint_scalars=data['lower_uses_native_joint_scalars'],
    lowerarm_interpolation=data['lowerarm_interpolation'],
    source_lower_hinge_fit_residual_radians={p['name']: p['anatomy']['native_hinge_model_residual_radians']
                                            for p in data['poses']},
    prepare_seconds=data['prepare_seconds'], hold_seconds=data['hold_seconds'],
    push_start_seconds=data['push_start_seconds'], contact_seconds=data['contact_seconds'],
    contact_brake_seconds=data['contact_brake_seconds'],
    recover_start_seconds=data['recover_start_seconds'], duration_seconds=data['duration_seconds'],
    extension_seconds=0., forward_wrist_displacement_cm=data['forward_wrist_displacement_cm'],
    brake_seconds=0., rebound_seconds=0., recovery_seconds=data['recovery_seconds'],
    uses_forward_push=False, uses_contact_brake=False, uses_short_rebound=False,
    extension_curve=None, brake_rebound_curve=None,
    clock_interface='MotionBlend(Age) returns a fractional key index with per-segment curve applied',
    fps=FPS, frames_including_endpoint=end+1,
    ue_build_started=False, editor_started=False, runtime_tested=False, rendered=False),
    indent=2) + '\n', encoding='utf-8')
print('SAVED_DOOR_PUSH_EDITABLE', str(output), action.name, flush=True)
