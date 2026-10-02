"""Save a V14 carry-based editable staff free-left quick punch take.

Only the complete left chain is changed. The right arm/staff carry pose comes
from the existing native V14 source. Background production; no render or UE.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
data = json.loads((P / 'full-pose.json').read_text(encoding='utf-8'))
base = ROOT / 'SourceAssets/ApprenticeStaff20260927/RightCarryV14/Staff_BowBasedGrip_V14.blend'
bpy.ops.wm.open_mainfile(filepath=str(base))
bpy.context.preferences.filepaths.save_version = 0
rig = bpy.data.objects['Staff_V7_BowGrasp_V14']
rig.name = 'Staff_V7_QuickPunch_20261001'
scene = bpy.context.scene
S = Matrix.Diagonal((1, -1, 1))
poses = [{n: Matrix(m) for n, m in pose['local'].items()} for pose in data['poses']]


def convert(m):
    out = (S @ m.to_3x3() @ S).to_4x4()
    out.translation = S @ m.translation * .01
    return out


def ease(u):
    u = max(0., min(1., u))
    return u * u * u * (u * (u * 6. - 15.) + 10.)


# A static carry copy retains the accepted full right chain and staff contact.
# Left keys replace the copied one-frame pose; no inherited two-second idle
# motion extends this short non-looping take.
action = bpy.data.actions['Pose_Staff_false_Idle'].copy()
action.name = 'A_Staff_FreeLeft_QuickPunch_20261001'
action.use_fake_user = True
action['contact_seconds'] = data['contact_seconds']
action['duration_seconds'] = data['duration_seconds']
action['revision'] = data['revision']
action['runtime_table'] = 'StaffAuthoredQuickPunch20261001.h'
action['interpolation'] = data['interpolation']
action['right_carry'] = data['right_carry']
action['forward_stroke_speed_multiplier'] = data['clock_mapping']['forward_stroke_speed_multiplier']
action['thumb_opposition'] = data['thumb_opposition']
action['close_sequence'] = data['close_sequence']
rig.animation_data.action = action
if len(action.slots):
    rig.animation_data.action_slot = action.slots[0]
previous = {}
last_frame = data['duration_seconds'] * scene.render.fps
frames = sorted(set([float(f) for f in range(math.ceil(last_frame))] +
                    [t * scene.render.fps for t in data['times']]))
for f in frames:
    time = f / scene.render.fps
    a = max(0, min(len(data['times']) - 2,
                   next((i - 1 for i, t in enumerate(data['times']) if t >= time and i > 0), len(data['times']) - 2)))
    b = a + 1
    alpha = ease((time - data['times'][a]) / (data['times'][b] - data['times'][a]))
    for n in data['order']:
        ka, kb = poses[a][n], poses[b][n]
        relative = ka.to_quaternion().slerp(kb.to_quaternion(), alpha).to_matrix().to_4x4()
        relative.translation = ka.translation.lerp(kb.translation, alpha)
        bone = rig.pose.bones[n]
        rest_bone = rig.data.bones[n]
        rest_local = rest_bone.parent.matrix_local.inverted() @ rest_bone.matrix_local
        bone.rotation_mode = 'QUATERNION'
        bone.matrix_basis = rest_local.inverted() @ convert(relative)
        if n in previous and bone.rotation_quaternion.dot(previous[n]) < 0:
            bone.rotation_quaternion.negate()
        previous[n] = bone.rotation_quaternion.copy()
        for prop in ('location', 'rotation_quaternion', 'scale'):
            bone.keyframe_insert(prop, frame=f)
# The dense samples already contain the authored easing. Linear keys preserve
# those samples; an additional Bezier curve can overshoot finger/arm channels.
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for key in curve.keyframe_points:
                    key.interpolation = 'LINEAR'
action.use_frame_range = True
action.frame_start = 0.
action.frame_end = last_frame
scene.frame_start = 0
scene.frame_end = math.ceil(last_frame)
scene.frame_set(0)
for marker in list(scene.timeline_markers):
    scene.timeline_markers.remove(marker)
for key in data['poses']:
    scene.timeline_markers.new(key['name'], frame=round(key['time'] * scene.render.fps))
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'Staff_FreeLeft_QuickPunch_20261001.blend'))
(P / 'editable-source.json').write_text(json.dumps({
    'revision': data['revision'], 'source': 'Staff_FreeLeft_QuickPunch_20261001.blend',
    'take': action.name, 'fps': scene.render.fps,
    'duration_seconds': data['duration_seconds'], 'contact_seconds': data['contact_seconds'],
    'left_runtime_table': 'StaffAuthoredQuickPunch20261001.h',
    'right_source': '../ApprenticeStaff20260927/RightCarryV14/Staff_BowBasedGrip_V14.blend',
    'fist_profile': data['fist_profile_source'], 'clock_mapping': data['clock_mapping'],
    'ue_asset_import_required': False, 'rendered': False, 'runtime_tested': False
}, indent=2), encoding='utf-8')
print('Saved editable staff left quick punch take; existing right carry retained; no render or runtime test.', flush=True)
