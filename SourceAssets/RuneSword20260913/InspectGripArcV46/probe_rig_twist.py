"""Twist about each bone's own axis, in rig space, without the +-180 ambiguity.

``local_rest^-1 @ local_pose`` is the bone's pose rotation expressed in the
bone's own rest frame, so its Y component is that joint's twist for this rig.
Swing (flexion / abduction) lives in X and Z and is reported separately.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
FPS = 120.0
CLIP = 'A_RuneSword_Inspect'
WATCH = ('upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l', 'lowerarm_l',
         'lowerarm_twist_01_l', 'lowerarm_twist_02_l', 'hand_l',
         'upperarm_r', 'upperarm_twist_01_r', 'upperarm_twist_02_r', 'lowerarm_r',
         'lowerarm_twist_01_r', 'lowerarm_twist_02_r', 'hand_r')

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
local_rest = {n: (rest[parent[n]].inverted() @ rest[n]) if parent[n] else rest[n]
              for n in rest}
action = bpy.data.actions[CLIP]
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
start, end = map(int, action.frame_range)


def twist_and_swing(name, pose):
    m = pose[name] if parent[name] is None else pose[parent[name]].inverted() @ pose[name]
    q = (local_rest[name].inverted() @ m).to_quaternion()
    twist = math.degrees(2.0 * math.atan2(q.y, q.w))
    axis, angle = q.to_axis_angle()
    swing = math.degrees(angle) * math.sqrt(max(0.0, 1.0 - axis.y * axis.y))
    return twist, swing


rows = []
for f in range(start, end + 1, 3):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
    row = {'frame': f, 'seconds': round(f / FPS, 4)}
    for name in WATCH:
        twist, swing = twist_and_swing(name, pose)
        row[name + '_twist'] = round(twist, 2)
        row[name + '_swing'] = round(swing, 2)
    rows.append(row)

(P / 'probe_rig_twist.json').write_text(
    json.dumps({'source': str(SOURCE), 'rows': rows}, indent=2), encoding='utf-8')

cols = ('upperarm_r', 'lowerarm_r', 'hand_r', 'upperarm_l', 'lowerarm_l', 'hand_l')
print('%-7s %-7s | ' % ('frame', 'sec') + ' '.join('%16s' % c for c in cols))
for row in rows:
    print('%-7d %-7.3f | ' % (row['frame'], row['seconds'])
          + ' '.join('%7.1f/%7.1f' % (row[c + '_twist'], row[c + '_swing'])
                     for c in cols))
print('PROBE_RIG_TWIST_DONE')
