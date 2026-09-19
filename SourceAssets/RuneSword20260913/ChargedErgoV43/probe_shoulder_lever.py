"""Test the humeral-roll lever: how far does the elbow seam drop, where does it go?"""
import bpy, json, math, sys
from mathutils import Matrix, Quaternion, Vector
from pathlib import Path

P = Path(__file__).parent
sys.path.insert(0, str(P))
import twist_distribution as td

SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
FPS = 480.0
TIMES = {'HeavyCharge': (0.20, 0.35, 0.50, 0.65, 1.00, 1.40, 2.00),
         'HeavyRelease': (0.075, 0.15, 0.40, 0.60, 0.80)}
GAINS = (0.0, 0.5, 1.0)
UP = 'upperarm_l'
UPT1 = 'upperarm_twist_01_l'
UPT2 = 'upperarm_twist_02_l'


def axial(delta, no_roll, axis):
    relative = delta @ no_roll.inverted()
    vector = Vector((relative.x, relative.y, relative.z))
    angle = 2.0 * math.atan2(vector.dot(axis), relative.w)
    return math.degrees((angle + math.pi) % (2.0 * math.pi) - math.pi)


def shoulder_metric(pose, rest, clav='clavicle_l', child=UP, tail='lowerarm_l'):
    """Same construction as the elbow metric, one joint up."""
    parent = pose[clav]
    bone = pose[child]
    axis = (pose[tail].translation - bone.translation).normalized()
    rest_child = (rest[tail].translation - rest[child].translation).normalized()
    up_delta = parent.to_quaternion() @ rest[clav].to_quaternion().inverted()
    bone_delta = bone.to_quaternion() @ rest[child].to_quaternion().inverted()
    no_roll = (up_delta @ rest_child).rotation_difference(axis) @ up_delta
    return axial(bone_delta, no_roll, axis)


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}

rows = []
for clip, times in TIMES.items():
    action = bpy.data.actions['A_RuneSword_' + clip]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    for t in times:
        scene.frame_set(int(round(t * FPS)))
        bpy.context.view_layer.update()
        pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
        info = td.forearm_roll(pose, rest)
        phi = math.degrees(info['roll'])
        entry = {'clip': clip, 'seconds': t, 'authored_elbow_deg': phi,
                 'shoulder_before_deg': shoulder_metric(pose, rest)}
        for gain in GAINS:
            roll = math.radians(phi * gain)
            humerus = Matrix.LocRotScale(
                pose[UP].translation,
                Quaternion(info['axis_humerus'] if 'axis_humerus' in info
                           else (pose['lowerarm_l'].translation - pose[UP].translation).normalized(),
                           roll) @ pose[UP].to_quaternion(),
                pose[UP].decompose()[2])
            modified = dict(pose)
            modified[UP] = humerus
            new_info = td.forearm_roll(modified, rest)
            entry['gain_%.1f_elbow_deg' % gain] = math.degrees(new_info['roll'])
            entry['gain_%.1f_shoulder_deg' % gain] = shoulder_metric(modified, rest)
        rows.append(entry)

(P / 'shoulder_lever.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print('%-14s %6s | %10s %10s %10s | %10s %10s %10s'
      % ('clip', 't', 'elbow g0', 'elbow g.5', 'elbow g1', 'shldr g0', 'shldr g.5', 'shldr g1'))
for row in rows:
    print('%-14s %6.3f | %10.1f %10.1f %10.1f | %10.1f %10.1f %10.1f'
          % (row['clip'], row['seconds'], row['gain_0.0_elbow_deg'], row['gain_0.5_elbow_deg'],
             row['gain_1.0_elbow_deg'], row['gain_0.0_shoulder_deg'], row['gain_0.5_shoulder_deg'],
             row['gain_1.0_shoulder_deg']))
print('PROBE_SHOULDER_LEVER_DONE')
