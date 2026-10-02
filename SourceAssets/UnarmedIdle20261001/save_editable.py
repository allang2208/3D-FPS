"""Save the actual editable V7 two-fist breathing take in background Blender.

Uses the same two native local endpoints, cosine clock and normalized
quaternion lerp as the game table. No renderer, UE import or game is started.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
data = json.loads((P / 'full-pose.json').read_text(encoding='utf-8'))
base = ROOT / 'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/M4_BareArmsV7.blend'
bpy.ops.wm.open_mainfile(filepath=str(base))
bpy.context.preferences.filepaths.save_version = 0
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE'
           and all(n in o.data.bones for n in ('clavicle_l', 'clavicle_r', 'hand_l', 'hand_r')))
rig.name = 'Unarmed_V7_ClosedFistIdle_20261001'
rig['runtime_table'] = 'UnarmedAuthoredIdle20261001.h'
rig['revision'] = data['revision']
rig['source'] = 'SourceAssets/UnarmedIdle20261001/full-pose.json'
rig['right_fist_transfer'] = data['right_fist_transfer']
rig.animation_data_create()
rig.animation_data_clear()
rig.animation_data_create()
scene = bpy.context.scene
FPS = 120
scene.render.fps = FPS
period = data['period_seconds']
mirror = Matrix.Diagonal((1., -1., 1.))
poses = [{n: Matrix(m) for n, m in pose['local'].items()} for pose in data['poses']]


def convert(m):
    result = (mirror @ m.to_3x3() @ mirror).to_4x4()
    result.translation = mirror @ m.translation * .01
    return result


def mix(a, b, alpha):
    qa, qb = a.to_quaternion(), b.to_quaternion()
    if qa.dot(qb) < 0:
        qb.negate()
    q = qa * (1. - alpha) + qb * alpha
    q.normalize()
    m = q.to_matrix().to_4x4()
    m.translation = a.translation.lerp(b.translation, alpha)
    return m


action = bpy.data.actions.new('A_Unarmed_V7_ClosedFistIdle_Breath_20261001')
action.use_fake_user = True
action['revision'] = data['revision']
action['period_seconds'] = period
action['source'] = 'SourceAssets/UnarmedIdle20261001/full-pose.json'
action['runtime_interpolation'] = data['breathing']['interpolation']
action['weight'] = data['breathing']['weight']
rig.animation_data.action = action
last_frame = round(period * FPS)
previous = {}
for frame in range(last_frame + 1):
    # Explicit equal endpoint eliminates floating point phase residue at loop.
    alpha = 0. if frame == last_frame else .5 - .5 * math.cos(2. * math.pi * frame / last_frame)
    for n in data['order']:
        relative = mix(poses[0][n], poses[1][n], alpha)
        bone = rig.pose.bones[n]
        ref = rig.data.bones[n].matrix_local
        if bone.parent:
            ref = rig.data.bones[bone.parent.name].matrix_local.inverted() @ ref
        bone.rotation_mode = 'QUATERNION'
        bone.matrix_basis = ref.inverted() @ convert(relative)
        if n in previous and bone.rotation_quaternion.dot(previous[n]) < 0:
            bone.rotation_quaternion.negate()
        previous[n] = bone.rotation_quaternion.copy()
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
action.frame_start = 0.
action.frame_end = float(last_frame)
scene.frame_start, scene.frame_end = 0, last_frame
scene.timeline_markers.clear()
for name, frame in [('Exhale', 0), ('Inhale', last_frame // 2), ('Exhale_Loop', last_frame)]:
    scene.timeline_markers.new(name, frame=frame)
scene.frame_set(0)
output = P / 'Unarmed_V7_ClosedFistIdle_20261001.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output))
(P / 'editable-source.json').write_text(json.dumps(dict(
    revision=data['revision'], source=output.name, take=action.name,
    source_input=base.relative_to(ROOT).as_posix(), fps=FPS,
    frames_including_loop_endpoint=last_frame + 1, period_seconds=period,
    runtime_table='Source/FPSGAME/Weapons/Unarmed/UnarmedAuthoredIdle20261001.h',
    interpolation='Same local normalized quaternion lerp and cosine weight as runtime; 120 Hz samples',
    keys=['Exhale', 'Inhale'], loop_endpoint_equal=True,
    authored_skin='Accepted BarePalmV7/M4, native bind and skin retained',
    ue_asset_import_required=False, rendered=False, runtime_tested=False), indent=2) + '\n', encoding='utf-8')
print('SAVED_UNARMED_IDLE_EDITABLE', str(output), action.name, flush=True)
