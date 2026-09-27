"""Save V16 free-hand loops on the existing V14 editable staff rig.

Only the 27 left-arm channels are keyed. The staff, right-hand contact and
existing right arm tracks are inherited from V14. No render or UE launch.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector

P = Path(__file__).resolve().parent
data = json.loads((P / 'left-gait.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(P.parent / 'RightCarryV14/Staff_BowBasedGrip_V14.blend'))
bpy.context.preferences.filepaths.save_version = 0
rig = bpy.data.objects['Staff_V7_BowGrasp_V14']
rig.name = 'Staff_V7_FreeLeftGait_V16'
scene = bpy.context.scene
S = Matrix.Diagonal((1, -1, 1))
cycles = {name: [{n: Matrix(m) for n, m in frame['local'].items()} for frame in frames]
          for name, frames in data['cycles'].items()}


def convert(m):
    out = (S @ m.to_3x3() @ S).to_4x4()
    out.translation = S @ m.translation * .01
    return out


for role, duration in [('Walk', 1.), ('Run', .7)]:
    action = bpy.data.actions['A_Staff_' + role + '_V14'].copy()
    action.name = 'A_Staff_' + role + '_V16_FreeLeft'
    action.use_fake_user = True
    action['phase_clock'] = data['phase_clock']
    action['stride_samples'] = data['samples_per_stride']
    action['runtime_blend'] = 'distance phase; MoveWeight + RunWeight, independent of display FPS'
    action['finger_follow'] = 'digit-specific lag and MCP/PIP/DIP flexion; wrist follows shoulder/elbow'
    action['runtime_variation'] = data['runtime_variation']
    rig.animation_data.action = action
    if len(action.slots):
        rig.animation_data.action_slot = action.slots[0]
    previous = {}
    end = round(duration * scene.render.fps)
    for f in range(end + 1):
        sample = f / end * data['samples_per_stride']
        a = math.floor(sample) % data['samples_per_stride']
        b = (a + 1) % data['samples_per_stride']
        alpha = sample - math.floor(sample)
        for n in data['order']:
            key_a, key_b = cycles[role][a][n], cycles[role][b][n]
            relative = key_a.to_quaternion().slerp(key_b.to_quaternion(), alpha).to_matrix().to_4x4()
            relative.translation = key_a.translation.lerp(key_b.translation, alpha)
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

rig.animation_data.action = bpy.data.actions['A_Staff_Walk_V16_FreeLeft']
if len(rig.animation_data.action.slots):
    rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_start = 0
scene.frame_end = scene.render.fps
scene.frame_set(scene.render.fps // 2)
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'Staff_FreeLeftGait_V16.blend'))
(P / 'editable-source.json').write_text(json.dumps({
    'revision': 16, 'source': 'Staff_FreeLeftGait_V16.blend',
    'takes': ['A_Staff_Walk_V16_FreeLeft', 'A_Staff_Run_V16_FreeLeft'],
    'fps': scene.render.fps, 'left_runtime_table': 'StaffAuthoredLeftGaitV16.h',
    'runtime_amplitude_variation_baked': False,
    'right_source': '../RightCarryV14/Staff_BowBasedGrip_V14.blend',
    'ue_asset_import_required': False, 'rendered': False, 'runtime_tested': False
}, indent=2), encoding='utf-8')
print('Saved editable V16 Walk/Run free-left-arm takes; no render or runtime test.', flush=True)
