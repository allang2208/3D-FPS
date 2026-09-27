"""Keep V16 free-hand motion and advance only the charged right-arm pose.

The runtime transports the complete authored right chain with the contact.
On this editable rig the equivalent translation belongs to clavicle_r; the
hand and staff_grip are descendants and must not be translated a second time.
Background authoring only, no render or game test.
"""
import bpy
import json
import re
from pathlib import Path
from mathutils import Vector

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
motion = (ROOT / 'Source/FPSGAME/Weapons/Staff/StaffCastMotion.h').read_text()
forward = float(re.search(r'ChargeForwardCm\s*=\s*([\d.]+)f', motion).group(1))
bpy.ops.wm.open_mainfile(filepath=str(P.parent / 'LeftGaitV16/Staff_FreeLeftGait_V16.blend'))
bpy.context.preferences.filepaths.save_version = 0
rig = bpy.data.objects['Staff_V7_FreeLeftGait_V16']
rig.name = 'Staff_ChargeForward_V17'
scene = bpy.context.scene
fps = scene.render.fps
clavicle = rig.pose.bones['clavicle_r']
# Existing action parents above the clavicle retain their native rest frame.
delta_basis = rig.data.bones['clavicle_r'].matrix_local.to_3x3().inverted() @ Vector((forward * .01, 0, 0))


def ease(t):
    t = max(0., min(1., t))
    return t * t * t * (t * (t * 6 - 15) + 10)


def copy_shifted_action(source, name, duration, weight):
    action = bpy.data.actions[source].copy()
    action.name = name
    action.use_fake_user = True
    action['charge_forward_cm'] = forward
    rig.animation_data.action = action
    if len(action.slots):
        rig.animation_data.action_slot = action.slots[0]
    keys = []
    for frame in range(round(duration * fps) + 1):
        scene.frame_set(frame)
        keys.append((frame, clavicle.location.copy() + delta_basis * weight(frame / fps)))
    # Read the existing take before writing keys to avoid cumulative offsets.
    for frame, position in keys:
        clavicle.location = position
        clavicle.keyframe_insert('location', frame=frame)


copy_shifted_action('A_Staff_Raise_V14', 'A_Staff_Raise_V17', .2, lambda t: ease(t / .2))
copy_shifted_action('A_Staff_Release_V14', 'A_Staff_Release_V17', .28,
                    lambda t: 1 - ease((t - .035) / (.18 - .035)))
for variant in ('false', 'alloy_grip', 'pine_grip', 'sandalwood_grip'):
    for role in ('Raised', 'Windup'):
        name = 'Pose_Staff_' + variant + '_' + role
        copy_shifted_action(name, name + '_V17', 0., lambda t: 1.)

rig.animation_data.action = bpy.data.actions['A_Staff_Raise_V17']
if len(rig.animation_data.action.slots):
    rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_start = 0
scene.frame_end = round(.2 * fps)
scene.frame_set(scene.frame_end)
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'Staff_ChargeForward_V17.blend'))
(P / 'editable-source.json').write_text(json.dumps({
    'revision': 17, 'source': 'Staff_ChargeForward_V17.blend', 'charge_forward_cm': forward,
    'camera_axis': '+X', 'fps': fps,
    'updated_takes': ['A_Staff_Raise_V17', 'A_Staff_Release_V17'],
    'static_pose_updates': 'Raised and Windup, all four grip variants',
    'left_gait': 'V16 takes retained', 'runtime': 'StaffCastMotion.h, complete contact transport',
    'ue_asset_import_required': False, 'rendered': False, 'runtime_tested': False
}, indent=2), encoding='utf-8')
print(f'Saved editable charge pose, camera forward +{forward:g} cm. No render or runtime test.', flush=True)
