"""Save editable V7 idle/walk/run takes using the same local runtime blend.

Background source saving only; no render, animation import or UE launch.
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
rig.name = 'Unarmed_V7_Locomotion_20261001'
rig['runtime_table'] = 'UnarmedAuthoredLocomotion20261001.h'
rig['revision'] = data['revision']
rig['source'] = 'SourceAssets/UnarmedLocomotion20261001/full-pose.json'
rig['right_arm_transfer'] = data['right_arm_transfer']
rig.animation_data_clear()
rig.animation_data_create()
scene = bpy.context.scene
FPS = 120
scene.render.fps = FPS
mirror = Matrix.Diagonal((1., -1., 1.))
all_poses = {'Idle': data['idle'], **data['cycles']}


def convert(m):
    result = (mirror @ m.to_3x3() @ mirror).to_4x4()
    result.translation = mirror @ m.translation * .01
    return result


def pose_mix(a, b, alpha, name):
    ma, mb = Matrix(a['local'][name]), Matrix(b['local'][name])
    qa, qb = ma.to_quaternion(), mb.to_quaternion()
    if qa.dot(qb) < 0:
        qb.negate()
    q = qa * (1. - alpha) + qb * alpha
    q.normalize()
    if name in ('lowerarm_l', 'lowerarm_r'):
        side = name[-1]
        ja, jb = a['anatomy'][side], b['anatomy'][side]
        flex = ja['elbow_flexion_offset_radians'] * (1. - alpha) + jb['elbow_flexion_offset_radians'] * alpha
        roll = ja['forearm_roll_radians'] * (1. - alpha) + jb['forearm_roll_radians'] * alpha
        j = data['joint_definitions'][side]
        q = (Quaternion(Vector(j['elbow_hinge']), flex)
             @ Matrix(j['lower_rest_rotation']).to_quaternion()
             @ Quaternion(Vector(j['forearm_axis']), roll))
        q.normalize()
    result = q.to_matrix().to_4x4()
    result.translation = ma.translation.lerp(mb.translation, alpha)
    return result


takes = []
for role, duration in [('Idle', data['period_seconds']), ('Walk', 1.), ('Run', .7)]:
    action = bpy.data.actions.new('A_Unarmed_V7_' + role + '_20261001')
    action.use_fake_user = True
    action['revision'] = data['revision']
    action['source'] = 'SourceAssets/UnarmedLocomotion20261001/full-pose.json'
    action['runtime_interpolation'] = data['lowerarm_interpolation'] + '; ' + data['other_bone_interpolation']
    action['phase_clock'] = data['phase_clock']
    action['right_phase_offset_radians'] = data['right_phase_offset_radians']
    action['editor_duration_only'] = 'Walk 1.0s / Run 0.7s; game speed is driven by footstep stride distance'
    rig.animation_data.action = action
    end = round(duration * FPS)
    previous = {}
    for frame in range(end + 1):
        if role == 'Idle':
            a, b = data['idle']
            alpha = 0. if frame == end else .5 - .5 * math.cos(math.tau * frame / end)
        else:
            sample = 0. if frame == end else frame / end * data['samples_per_stride']
            ia = math.floor(sample) % data['samples_per_stride']
            a, b = data['cycles'][role][ia], data['cycles'][role][(ia + 1) % data['samples_per_stride']]
            alpha = sample - math.floor(sample)
        for name in data['order']:
            relative = pose_mix(a, b, alpha, name)
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
                    curve.modifiers.new('CYCLES')
    action.use_frame_range = True
    action.frame_start, action.frame_end = 0., float(end)
    takes.append(dict(role=role, action=action.name, fps=FPS, frames_including_endpoint=end + 1,
                      display_duration_seconds=duration, loop_endpoint_equal=True))
rig.animation_data.action = bpy.data.actions[takes[0]['action']]
if len(rig.animation_data.action.slots):
    rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_start, scene.frame_end = 0, round(data['period_seconds'] * FPS)
scene.timeline_markers.clear()
for name, frame in [('Exhale', 0), ('Inhale', scene.frame_end // 2), ('Exhale_Loop', scene.frame_end)]:
    scene.timeline_markers.new(name, frame=frame)
scene.frame_set(0)
output = P / 'Unarmed_V7_Locomotion_20261001.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output))
(P / 'editable-source.json').write_text(json.dumps(dict(
    revision=data['revision'], source=output.name, saved=True, source_input=base.relative_to(ROOT).as_posix(),
    takes=takes, runtime_table='Source/FPSGAME/Weapons/Unarmed/UnarmedAuthoredLocomotion20261001.h',
    idle_wrists_cm=data['new_idle_wrist_cm'], phase_clock=data['phase_clock'],
    right_arm_transfer=data['right_arm_transfer'],
    interpolation='Same normalized local quaternion lerp and scalar native elbow assembly as runtime; 120 Hz takes',
    source_skin='Accepted BarePalmV7/M4, original bind and skin retained',
    ue_asset_import_required=False, rendered=False, runtime_tested=False), indent=2) + '\n', encoding='utf-8')
print('SAVED_UNARMED_LOCOMOTION_EDITABLE', str(output), [t['action'] for t in takes], flush=True)
