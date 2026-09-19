"""How much of the forearm's axial difference is carried by the twist helpers?"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
FPS = 480.0

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}

WATCH = ('upperarm_l', 'lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l',
         'hand_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l', 'hand_r')


def local_delta(name, pose):
    """Rotation of the bone relative to its rest orientation, in its parent's space."""
    parent = rig.data.bones[name].parent
    m = pose[name] if parent is None else pose[parent.name].inverted() @ pose[name]
    r = (rest[parent.name].inverted() @ rest[name]) if parent else rest[name]
    return (r.inverted() @ m).to_quaternion()


def angle_deg(q):
    return math.degrees(2 * math.atan2(math.sqrt(q.x * q.x + q.y * q.y + q.z * q.z), abs(q.w)))


rows = []
for clip, seconds in (('HeavyCharge', (0.0, 0.12, 0.20, 0.35, 0.50, 0.65, 1.00, 1.40, 2.00)),
                      ('HeavyRelease', (0.02, 0.075, 0.40, 1.00))):
    action = bpy.data.actions['A_RuneSword_' + clip]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    for t in seconds:
        f = t * FPS
        scene.frame_set(int(f), subframe=f - int(f))
        bpy.context.view_layer.update()
        pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
        entry = {'clip': clip, 'seconds': t}
        for name in WATCH:
            entry[name] = angle_deg(local_delta(name, pose))
        rows.append(entry)

(P / 'twist_bones.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
header = 'clip            t     ' + ''.join('%-22s' % n for n in WATCH)
print(header)
for row in rows:
    print('%-15s %5.3f ' % (row['clip'], row['seconds'])
          + ''.join('%-22.1f' % row[n] for n in WATCH))
print('TWIST_BONES_DONE')
