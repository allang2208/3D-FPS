"""The twirl as seen from the palm: spin angle, axis and pivot of the grip change.

``G(t) = inverse(hand) x sword``; the twirl is ``dG(t) = inverse(G0) x G(t)``
where G0 is the grip at the start of the spin.  The fixed point of dG is the
contact point, expressed in the hand's frame, and is what has to sit on the
hilt for the move to read as controlled.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
FPS = 120.0
CLIP = 'A_RuneSword_Inspect'
START_SECONDS = 0.35

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
action = bpy.data.actions[CLIP]
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
start, end = map(int, action.frame_range)


def grip(frame):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    hand = rig.pose.bones['hand_r'].matrix
    weapon = rig.pose.bones['WPN_root'].matrix
    return (hand, weapon, hand.inverted() @ weapon)


g0_frame = int(START_SECONDS * FPS)
_, _, g0 = grip(g0_frame)

rows = []
previous_q = None
running = 0.0
for frame in range(start, end + 1, 1):
    hand, weapon, relative = grip(frame)
    delta = g0.inverted() @ relative
    translation, rotation, _ = delta.decompose()
    if previous_q is not None and rotation.dot(previous_q) < 0:
        rotation.negate()
    previous_q = rotation.copy()
    axis, angle = rotation.to_axis_angle()
    # Unwrapped spin accumulated along the sequence, so a full turn reads as
    # 360 and not as a jump back through zero.
    if frame > start:
        step = (rotation @ previous_step_q.inverted())
        step_axis, step_angle = step.to_axis_angle()
        sign = 1.0 if step_axis.dot(axis) >= 0 else -1.0
        running += sign * math.degrees(step_angle)
    previous_step_q = rotation.copy()
    pivot = None
    if abs(math.degrees(angle)) > 1e-6:
        inverse = (Matrix.Identity(3) - rotation.to_matrix())
        if abs(inverse.determinant()) > 1e-9:
            pivot = inverse.inverted() @ translation
    rows.append({
        'frame': frame, 'seconds': round((frame - start) / FPS, 4),
        'angle_deg': round(math.degrees(angle), 2),
        'spin_unwrapped_deg': round(running, 2),
        'axis': [round(v, 3) for v in axis],
        'pivot_hand_local_m': None if pivot is None else [round(v, 5) for v in pivot],
        'sword_head': [round(v, 4) for v in weapon.translation],
        'hand_head': [round(v, 4) for v in hand.translation],
        'grip_offset': [round(v, 5) for v in translation],
    })

(P / 'probe_twirl_pivot.json').write_text(
    json.dumps({'source': str(SOURCE), 'grip_reference_seconds': START_SECONDS,
                'rows': rows}, indent=2), encoding='utf-8')

print('%-7s %-7s %8s %10s %-20s %-30s' % ('frame', 'sec', 'angle', 'spin',
                                          'axis', 'pivot (hand local, m)'))
for row in rows:
    if 0.30 <= row['seconds'] <= 0.75:
        print('%-7d %-7.3f %8.1f %10.1f %-20s %-30s'
              % (row['frame'], row['seconds'], row['angle_deg'],
                 row['spin_unwrapped_deg'], row['axis'], row['pivot_hand_local_m']))
print('spin total over clip: %.1f deg' % rows[-1]['spin_unwrapped_deg'])
print('PROBE_TWIRL_PIVOT_DONE')
