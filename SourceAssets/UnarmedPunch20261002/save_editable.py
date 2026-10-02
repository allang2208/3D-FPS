"""Background-save both V7 unarmed punch takes; no render or UE launch."""
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
rig.name = 'Unarmed_V7_AlternatingPunch_20261002'
rig['runtime_table'] = 'UnarmedAuthoredPunch20261002.h'
rig['revision'] = data['revision']
rig['source'] = 'SourceAssets/UnarmedPunch20261002/full-pose.json'
rig['right_arm_transfer'] = data['right_arm_transfer']
rig.animation_data_clear()
rig.animation_data_create()
scene = bpy.context.scene
FPS = 120
scene.render.fps = FPS
mirror = Matrix.Diagonal((1., -1., 1.))
duration = data['duration_seconds']


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
        joint = data['joint_definitions'][side]
        q = (Quaternion(Vector(joint['elbow_hinge']), flex)
             @ Matrix(joint['lower_rest_rotation']).to_quaternion()
             @ Quaternion(Vector(joint['forearm_axis']), roll))
        q.normalize()
    result = q.to_matrix().to_4x4()
    result.translation = ma.translation.lerp(mb.translation, alpha)
    return result


# Keep exact author times (including the accelerated contact) as well as
# dense samples. Every baked key is linear so no second Bezier ease appears.
sample_times = sorted(set([i / FPS for i in range(math.floor(duration * FPS) + 1)] + data['times']))
takes = []
for role in ('Right', 'Left'):
    action = bpy.data.actions.new('A_Unarmed_V7_' + role + 'Punch_20261002')
    action.use_fake_user = True
    action['revision'] = data['revision']
    action['source'] = 'SourceAssets/UnarmedPunch20261002/full-pose.json'
    action['runtime_interpolation'] = data['lowerarm_interpolation'] + '; ' + data['other_bone_interpolation']
    action['contact_seconds'] = data['contact_seconds']
    rig.animation_data.action = action
    previous = {}
    key = 0
    for age in sample_times:
        while key < len(data['times']) - 2 and age >= data['times'][key + 1]:
            key += 1
        t = min(1., max(0., (age - data['times'][key]) / (data['times'][key + 1] - data['times'][key])))
        alpha = t * t * t * (t * (t * 6. - 15.) + 10.)
        a, b = data['poses'][role][key:key + 2]
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
                bone.keyframe_insert(prop, frame=age * FPS)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for point in curve.keyframe_points:
                        point.interpolation = 'LINEAR'
    action.use_frame_range = True
    action.frame_start, action.frame_end = 0., duration * FPS
    takes.append(dict(role=role, action=action.name, fps=FPS, samples=len(sample_times),
                      duration_seconds=duration, contact_seconds=data['contact_seconds'], exact_author_times=True))
rig.animation_data.action = bpy.data.actions[takes[0]['action']]
if len(rig.animation_data.action.slots):
    rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_start, scene.frame_end = 0, math.ceil(duration * FPS)
scene.timeline_markers.clear()
for pose in data['poses']['Right']:
    scene.timeline_markers.new(pose['name'], frame=round(pose['time'] * FPS))
scene.frame_set(0)
output = P / 'Unarmed_V7_AlternatingPunch_20261002.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output))
(P / 'editable-source.json').write_text(json.dumps(dict(
    revision=data['revision'], source=output.name, saved=True, source_input=base.relative_to(ROOT).as_posix(),
    takes=takes, runtime_table='Source/FPSGAME/Weapons/Unarmed/UnarmedAuthoredPunch20261002.h',
    baseline_source=data['baseline_source'], donor_source=data['donor_source'],
    right_arm_transfer=data['right_arm_transfer'],
    interpolation='Native hinge flex/roll assembly, normalized quaternion local blend and quintic segment ease; dense linear curves',
    source_skin='Accepted BarePalmV7/M4, original bind and skin retained',
    ue_asset_import_required=False, rendered=False, runtime_tested=False), indent=2) + '\n', encoding='utf-8')
print('SAVED_UNARMED_PUNCH_EDITABLE', str(output), [t['action'] for t in takes], flush=True)
