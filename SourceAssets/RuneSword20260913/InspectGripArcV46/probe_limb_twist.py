"""Local twist about the actual limb axis, for both arms and their twist helpers.

The rig's bones do not point along a fixed local component, so the axis is
derived per bone from the joint positions rather than assumed.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
FPS = 120.0
CLIP = 'A_RuneSword_Inspect'

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
local_rest = {n: (rest[parent[n]].inverted() @ rest[n]) if parent[n] else rest[n]
              for n in rest}


def axis_local(segment):
    lower, upper = segment
    direction = (rest[upper].translation - rest[lower].translation).normalized()
    return lower, upper, direction


def twist(name, segment, pose):
    lower, _, direction = axis_local(segment)
    axis = (rest[name].to_3x3().inverted() @ direction).normalized()
    delta = (local_rest[name].inverted()
             @ (pose[parent[name]].inverted() @ pose[name])).to_quaternion()
    if delta.w < 0.0:
        delta.negate()
    return math.degrees(2.0 * math.atan2(Vector((delta.x, delta.y, delta.z)).dot(axis),
                                         delta.w))


WATCH = {
    'upperarm_r': ('lowerarm_r', 'hand_r'),
    'upperarm_twist_01_r': ('lowerarm_r', 'hand_r'),
    'upperarm_twist_02_r': ('lowerarm_r', 'hand_r'),
    'lowerarm_r': ('lowerarm_r', 'hand_r'),
    'lowerarm_twist_01_r': ('lowerarm_r', 'hand_r'),
    'lowerarm_twist_02_r': ('lowerarm_r', 'hand_r'),
    'upperarm_l': ('lowerarm_l', 'hand_l'),
    'upperarm_twist_01_l': ('lowerarm_l', 'hand_l'),
    'upperarm_twist_02_l': ('lowerarm_l', 'hand_l'),
    'lowerarm_l': ('lowerarm_l', 'hand_l'),
    'lowerarm_twist_01_l': ('lowerarm_l', 'hand_l'),
    'lowerarm_twist_02_l': ('lowerarm_l', 'hand_l'),
}

action = bpy.data.actions[CLIP]
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
start, end = map(int, action.frame_range)
rows = []
for f in range(start, end + 1, 3):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
    rows.append({'frame': f, 'seconds': round(f / FPS, 4),
                 **{name: round(twist(name, segment, pose), 2)
                    for name, segment in WATCH.items()}})

(P / 'probe_limb_twist.json').write_text(
    json.dumps({'source': str(SOURCE), 'rows': rows}, indent=2), encoding='utf-8')

cols = ('upperarm_r', 'upperarm_twist_01_r', 'upperarm_twist_02_r', 'lowerarm_r',
        'lowerarm_twist_01_r', 'lowerarm_twist_02_r',
        'upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l', 'lowerarm_l',
        'lowerarm_twist_01_l', 'lowerarm_twist_02_l')
print('%-7s %-7s | ' % ('frame', 'sec') + ' '.join('%8s' % c.replace('_r', '').replace('_l', '')
                                                   for c in cols))
for row in rows:
    print('%-7d %-7.3f | ' % (row['frame'], row['seconds'])
          + ' '.join('%8.1f' % row[c] for c in cols))
print('PROBE_LIMB_TWIST_DONE')
