"""Read-only probe of the currently integrated Inspect (V42) plus live seam metrics.

Answers three questions before any authoring:
  1. What objects/bones/actions exist in the shipped source blend?
  2. How much axial shear sits on the elbow and wrist seams during the inspect?
  3. Do the forearm twist helper bones carry any of that rotation?
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


def axial_delta(pose_a, pose_b, rest_a, rest_b):
    """Signed twist of b relative to a, about the a->b bone axis (degrees)."""
    axis = (pose_b.translation - pose_a.translation).normalized()
    a_delta = pose_a.to_quaternion() @ rest_a.to_quaternion().inverted()
    b_delta = pose_b.to_quaternion() @ rest_b.to_quaternion().inverted()
    relative = b_delta @ a_delta.inverted()
    vector = Vector((relative.x, relative.y, relative.z))
    angle = 2.0 * math.atan2(vector.dot(axis), relative.w)
    return math.degrees((angle + math.pi) % (2.0 * math.pi) - math.pi)


def bone_twist(pose, name):
    """Rotation applied at this bone relative to its rest, as a single angle."""
    q = pose[name].to_quaternion() @ rest[name].to_quaternion().inverted()
    vector = Vector((q.x, q.y, q.z))
    return math.degrees(2.0 * math.atan2(vector.length, abs(q.w)))


report = {
    'source': str(SOURCE),
    'fps': scene.render.fps / scene.render.fps_base,
    'objects': sorted(o.name for o in bpy.data.objects),
    'actions': sorted(a.name for a in bpy.data.actions),
    'bone_names': [b.name for b in rig.data.bones],
    'character_bones': {n: parent[n] for n in parent if not n.startswith('RuneSword')},
}

action = bpy.data.actions[CLIP]
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
start, end = map(int, action.frame_range)
report['inspect_frames'] = [start, end]
report['inspect_seconds'] = (end - start) / FPS

WATCH = ('upperarm_l', 'lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l',
         'hand_l', 'upperarm_r', 'lowerarm_r', 'lowerarm_twist_01_r',
         'lowerarm_twist_02_r', 'hand_r', 'clavicle_l', 'clavicle_r')

rows = []
for f in range(start, end + 1, 3):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
    t = f / FPS
    row = {'frame': f, 'seconds': round(t, 4),
           'right_elbow_deg': axial_delta(pose['upperarm_r'], pose['lowerarm_r'],
                                          rest['upperarm_r'], rest['lowerarm_r']),
           'right_wrist_deg': axial_delta(pose['lowerarm_r'], pose['hand_r'],
                                          rest['lowerarm_r'], rest['hand_r']),
           'left_elbow_deg': axial_delta(pose['upperarm_l'], pose['lowerarm_l'],
                                         rest['upperarm_l'], rest['lowerarm_l']),
           'left_wrist_deg': axial_delta(pose['lowerarm_l'], pose['hand_l'],
                                         rest['lowerarm_l'], rest['hand_l'])}
    for name in WATCH:
        row[name] = round(bone_twist(pose, name), 2)
    for name in ('hand_r', 'hand_l', 'WPN_root'):
        row[name + '_pos'] = [round(v, 5) for v in pose[name].translation]
    rows.append(row)

report['rows'] = rows
(P / 'probe_inspect.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

print('objects:', ', '.join(report['objects']))
print('actions:', ', '.join(report['actions']))
print('inspect frames', start, end, 'seconds', report['inspect_seconds'])
print('%-7s %-7s %8s %8s %8s %8s | %8s %8s %8s %8s' % (
    'frame', 'sec', 'R-elbow', 'R-wrist', 'L-elbow', 'L-wrist',
    'h_l_ang', 'tw1_r', 'tw2_r', 'hand_r'))
for row in rows:
    print('%-7d %-7.3f %8.1f %8.1f %8.1f %8.1f | %8.1f %8.1f %8.1f %8.1f' % (
        row['frame'], row['seconds'], row['right_elbow_deg'], row['right_wrist_deg'],
        row['left_elbow_deg'], row['left_wrist_deg'], row['hand_l'],
        row['lowerarm_twist_01_r'], row['lowerarm_twist_02_r'], row['hand_r']))
print('PROBE_INSPECT_DONE')
