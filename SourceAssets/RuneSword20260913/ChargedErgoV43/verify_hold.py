"""V45 vs V44: elbow bend, reach, and whether the grips moved on the hilt."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
BLENDS = {'v44': P / 'AzureRunesword_ChargedShoulderV44.blend',
          'v45': P / 'AzureRunesword_ChargedHoldV45.blend'}
TIMES = {'HeavyCharge': (0.0, 0.35, 0.65, 1.20, 1.60, 2.00),
         'HeavyRelease': (0.0, 0.075, 0.40, 0.60, 0.80, 1.0)}
FPS = 480.0


def sample(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    rig = bpy.data.objects['SK_RuneSword_Rig']
    rows = {}
    for clip, times in TIMES.items():
        action = bpy.data.actions['A_RuneSword_' + clip]
        rig.animation_data.action = action
        rig.animation_data.action_slot = action.slots[0]
        for t in times:
            scene.frame_set(int(round(t * FPS)))
            bpy.context.view_layer.update()
            pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
            inv = pose['WPN_root'].inverted()
            entry = {'left_elbow_deg': 0.0, 'right_elbow_deg': 0.0, 'left_reach_m': 0.0}
            for side, key in (('l', 'left'), ('r', 'right')):
                S = pose['upperarm_' + side].translation
                E = pose['lowerarm_' + side].translation
                W = pose['hand_' + side].translation
                entry[key + '_elbow_deg'] = math.degrees(
                    (E - S).normalized().angle((W - E).normalized()))
                if side == 'l':
                    entry['left_reach_m'] = (W - S).length
                grip = inv @ pose['hand_' + side]
                entry[key + '_grip_offset_m'] = list(grip.translation)
                entry[key + '_grip_rot_deg'] = math.degrees(2 * math.atan2(
                    math.sqrt(sum(grip.to_quaternion()[i] ** 2 for i in range(3))),
                    abs(grip.to_quaternion().w)))
            rows['%s %.3f' % (clip, t)] = entry
    return rows


v44 = sample(BLENDS['v44'])
v45 = sample(BLENDS['v45'])
summary = {}
for key in v44:
    a, b = v44[key], v45[key]
    summary[key] = {
        'left_elbow_deg': [a['left_elbow_deg'], b['left_elbow_deg']],
        'right_elbow_deg': [a['right_elbow_deg'], b['right_elbow_deg']],
        'left_reach_m': [a['left_reach_m'], b['left_reach_m']],
        'left_grip_move_mm': (Vector(a['left_grip_offset_m'])
                              - Vector(b['left_grip_offset_m'])).length * 1000.0,
        'right_grip_move_mm': (Vector(a['right_grip_offset_m'])
                               - Vector(b['right_grip_offset_m'])).length * 1000.0,
        'left_grip_rot_delta_deg': abs(a['left_grip_rot_deg'] - b['left_grip_rot_deg']),
        'right_grip_rot_delta_deg': abs(a['right_grip_rot_deg'] - b['right_grip_rot_deg']),
    }
(P / 'verification_v45.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print('%-22s %14s %16s %16s %12s' % ('clip time', 'L elbow old/new', 'R elbow old/new',
                                     'L reach old/new', 'grip move mm'))
for key, e in summary.items():
    print('%-22s %6.1f -> %-6.1f %6.1f -> %-6.1f %5.3f -> %-5.3f  L %6.3f  R %6.3f  rot %.3f'
          % (key, e['left_elbow_deg'][0], e['left_elbow_deg'][1],
             e['right_elbow_deg'][0], e['right_elbow_deg'][1],
             e['left_reach_m'][0], e['left_reach_m'][1],
             e['left_grip_move_mm'], e['right_grip_move_mm'],
             max(e['left_grip_rot_delta_deg'], e['right_grip_rot_delta_deg'])))
print('VERIFY_HOLD_DONE')
