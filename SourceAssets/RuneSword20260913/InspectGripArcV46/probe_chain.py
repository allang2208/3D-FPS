"""Which bones actually carry the Inspect's arm rotation, and which carry skin?

Local delta = rotation of a bone relative to its own rest orientation, measured
in its parent's space. Authoring that puts the whole forearm/humerus roll on the
parent bone and leaves the twist helpers at ~0 is the seam-shear signature that
was already diagnosed for the charged attack.
"""
import bpy, json, math
from collections import Counter
from pathlib import Path

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
FPS = 120.0
CLIP = 'A_RuneSword_Inspect'

WATCH = {side: ('clavicle_' + side, 'upperarm_' + side,
                'upperarm_twist_01_' + side, 'upperarm_twist_02_' + side,
                'lowerarm_' + side, 'lowerarm_twist_01_' + side,
                'lowerarm_twist_02_' + side, 'hand_' + side)
         for side in ('l', 'r')}

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
local_rest = {n: (rest[parent[n]].inverted() @ rest[n]) if parent[n] else rest[n]
              for n in rest}


def local_angle(pose, name):
    m = pose[name] if parent[name] is None else pose[parent[name]].inverted() @ pose[name]
    q = (local_rest[name].inverted() @ m).to_quaternion()
    return math.degrees(2.0 * math.atan2(math.sqrt(q.x * q.x + q.y * q.y + q.z * q.z),
                                         abs(q.w)))


# Dominant vertex counts along each chain, so we know which bones the skin sees.
groups = {g.name: g.index for g in arms.vertex_groups}
dominant = Counter()
for vertex in arms.data.vertices:
    if not vertex.groups:
        continue
    best = max(vertex.groups, key=lambda g: g.weight)
    dominant[arms.vertex_groups[best.group].name] += 1

action = bpy.data.actions[CLIP]
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
start, end = map(int, action.frame_range)

rows = []
for f in range(start, end + 1, 6):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
    row = {'frame': f, 'seconds': round(f / FPS, 4)}
    for side in ('l', 'r'):
        for name in WATCH[side]:
            row[name] = round(local_angle(pose, name), 2)
    rows.append(row)

report = {'source': str(SOURCE), 'clip': CLIP, 'seconds': (end - start) / FPS,
          'dominant_vertex_counts': {n: dominant.get(n, 0) for side in ('l', 'r')
                                     for n in WATCH[side]},
          'rows': rows}
(P / 'probe_chain.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

names = ('lowerarm_r', 'lowerarm_twist_01_r', 'lowerarm_twist_02_r',
         'upperarm_r', 'upperarm_twist_01_r', 'upperarm_twist_02_r',
         'lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l')
print('dominant verts:', json.dumps({n: dominant.get(n, 0) for n in names}))
print('%-7s %-7s | ' % ('frame', 'sec') + ' '.join('%8s' % n[:9] for n in names))
for row in rows:
    print('%-7d %-7.3f | ' % (row['frame'], row['seconds'])
          + ' '.join('%8.2f' % row[n] for n in names))
print('PROBE_CHAIN_DONE')
