"""Compare the left and right elbow's axial difference and twist distribution."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
FPS = 480.0
SIDES = ('l', 'r')

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}


def elbow_roll(pose, side):
    up, fore, hand = 'upperarm_%s' % side, 'lowerarm_%s' % side, 'hand_%s' % side
    A = pose[up].translation
    E = pose[fore].translation
    H = pose[hand].translation
    ud = (E - A).normalized()
    fd = (H - E).normalized()
    rest_up = (rest[fore].translation - rest[up].translation).normalized()
    rest_fore = (rest[hand].translation - rest[fore].translation).normalized()
    uq = pose[up].to_quaternion() @ rest[up].to_quaternion().inverted()
    fq = pose[fore].to_quaternion() @ rest[fore].to_quaternion().inverted()
    no_roll = (uq @ rest_fore).rotation_difference(fd) @ uq
    relative = fq @ no_roll.inverted()
    axis = Vector((relative.x, relative.y, relative.z))
    roll = 2 * math.atan2(axis.dot(fd), relative.w)
    roll = (roll + math.pi) % (2 * math.pi) - math.pi
    return {
        'flex_deg': math.degrees(ud.angle(fd)),
        'roll_deg': math.degrees(roll),
        'wrist_deg': math.degrees(fd.angle(pose[hand].to_quaternion()
                                           @ rest[hand].to_quaternion().inverted() @ rest_fore)),
    }


def local_delta_deg(pose, name):
    parent = rig.data.bones[name].parent
    m = pose[name] if parent is None else pose[parent.name].inverted() @ pose[name]
    r = (rest[parent.name].inverted() @ rest[name]) if parent else rest[name]
    q = (r.inverted() @ m).to_quaternion()
    return math.degrees(2 * math.atan2(math.sqrt(q.x * q.x + q.y * q.y + q.z * q.z), abs(q.w)))


TIMES = {'HeavyCharge': (0.0, 0.12, 0.20, 0.35, 0.50, 0.65, 1.00, 1.40, 2.00),
         'HeavyRelease': (0.02, 0.075, 0.15, 0.40, 0.60, 1.00)}

rows = []
for clip, times in TIMES.items():
    action = bpy.data.actions['A_RuneSword_' + clip]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    for t in times:
        f = t * FPS
        scene.frame_set(int(f), subframe=f - int(f))
        bpy.context.view_layer.update()
        pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
        row = {'clip': clip, 'seconds': t}
        for side in SIDES:
            metrics = elbow_roll(pose, side)
            row['%s_flex' % side] = metrics['flex_deg']
            row['%s_roll' % side] = metrics['roll_deg']
            row['%s_wrist' % side] = metrics['wrist_deg']
            for bone in ('lowerarm_twist_01', 'lowerarm_twist_02'):
                row['%s_%s' % (side, bone)] = local_delta_deg(pose, '%s_%s' % (bone, side))
        rows.append(row)

(P / 'compare_arms.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print('clip           t      L_flex L_roll L_wrist  L_tw1 L_tw2 | R_flex R_roll R_wrist  R_tw1 R_tw2')
for row in rows:
    print('%-14s %5.2f  %6.1f %6.1f %7.1f %6.1f %6.1f | %6.1f %6.1f %7.1f %6.1f %6.1f' % (
        row['clip'], row['seconds'], row['l_flex'], row['l_roll'], row['l_wrist'],
        row['l_lowerarm_twist_01'], row['l_lowerarm_twist_02'],
        row['r_flex'], row['r_roll'], row['r_wrist'],
        row['r_lowerarm_twist_01'], row['r_lowerarm_twist_02']))
print('COMPARE_ARMS_DONE')
