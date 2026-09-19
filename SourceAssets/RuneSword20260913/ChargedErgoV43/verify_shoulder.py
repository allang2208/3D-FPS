"""V44 kinematics: what moved, what did not, and the elbow metric per phase."""
import bpy, json, math, sys
import numpy as np
from pathlib import Path

P = Path(__file__).parent
sys.path.insert(0, str(P))
import shoulder_transport as st

OLD = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
NEW = P / 'AzureRunesword_ChargedShoulderV44.blend'
FPS = 480.0
CLIPS = ('HeavyCharge', 'HeavyRelease', 'Slash1')
STRIDE = 2


def sample(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    rig = bpy.data.objects['SK_RuneSword_Rig']
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    result = {}
    for clip in CLIPS:
        action = bpy.data.actions['A_RuneSword_' + clip]
        rig.animation_data.action = action
        rig.animation_data.action_slot = action.slots[0]
        start, end = map(int, action.frame_range)
        frames = []
        for f in range(start, end + 1, STRIDE):
            scene.frame_set(f)
            bpy.context.view_layer.update()
            pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
            frames.append({
                'seconds': f / FPS,
                'positions': {b.name: pose[b.name].translation.copy() for b in rig.pose.bones},
                'hand_rotation': pose[st.HAND].to_quaternion().copy(),
                'upper_dir': (pose[st.LO].translation - pose[st.UP].translation).normalized(),
                'fore_dir': (pose[st.HAND].translation - pose[st.LO].translation).normalized(),
                'upper_len': (pose[st.LO].translation - pose[st.UP].translation).length,
                'fore_len': (pose[st.HAND].translation - pose[st.LO].translation).length,
                'elbow': st.elbow_roll(pose, rest),
            })
        result[clip] = frames
    return result


old = sample(OLD)
new = sample(NEW)
summary = {}
for clip in CLIPS:
    a, b = old[clip], new[clip]
    worst_position = 0.0
    worst_bone = ''
    worst_hand = worst_upper = worst_fore = worst_length = 0.0
    before_max = after_max = 0.0
    for x, y in zip(a, b):
        for name, value in x['positions'].items():
            delta = (value - y['positions'][name]).length * 1000.0
            if delta > worst_position:
                worst_position, worst_bone = delta, name
        hand = x['hand_rotation'].rotation_difference(y['hand_rotation'])
        worst_hand = max(worst_hand, math.degrees(2 * math.atan2(
            math.sqrt(hand.x ** 2 + hand.y ** 2 + hand.z ** 2), abs(hand.w))))
        worst_upper = max(worst_upper, math.degrees(x['upper_dir'].angle(y['upper_dir'])))
        worst_fore = max(worst_fore, math.degrees(x['fore_dir'].angle(y['fore_dir'])))
        worst_length = max(worst_length, abs(x['upper_len'] - y['upper_len']) * 1000.0,
                           abs(x['fore_len'] - y['fore_len']) * 1000.0)
        before_max = max(before_max, abs(x['elbow']))
        after_max = max(after_max, abs(y['elbow']))
    summary[clip] = {
        'samples': len(a), 'seconds': a[-1]['seconds'],
        'max_bone_position_delta_mm': worst_position, 'worst_bone': worst_bone,
        'max_hand_world_rotation_delta_deg': worst_hand,
        'max_upperarm_direction_delta_deg': worst_upper,
        'max_forearm_direction_delta_deg': worst_fore,
        'max_arm_length_delta_mm': worst_length,
        'elbow_metric_abs_max_before': before_max,
        'elbow_metric_abs_max_after': after_max,
    }
(P / 'verification_v44.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
for clip, e in summary.items():
    print('===', clip, '(%d samples, %.3f s)' % (e['samples'], e['seconds']))
    print('   bone position delta %10.6f mm (%s)' % (e['max_bone_position_delta_mm'], e['worst_bone']))
    print('   hand world rot      %10.6f deg' % e['max_hand_world_rotation_delta_deg'])
    print('   direction delta     upper %9.6f / forearm %9.6f deg'
          % (e['max_upperarm_direction_delta_deg'], e['max_forearm_direction_delta_deg']))
    print('   arm length delta    %10.6f mm' % e['max_arm_length_delta_mm'])
    print('   elbow metric        %8.1f -> %8.1f deg (max over clip)'
          % (e['elbow_metric_abs_max_before'], e['elbow_metric_abs_max_after']))
print('VERIFY_SHOULDER_DONE')
