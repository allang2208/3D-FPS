"""Elbow and shoulder axial metrics, authored vs V44."""
import bpy, json, math, sys
from mathutils import Vector
from pathlib import Path

P = Path(__file__).parent
sys.path.insert(0, str(P))
import shoulder_transport as st

BLENDS = {'authored': P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend',
          'v44': P / 'AzureRunesword_ChargedShoulderV44.blend'}
TIMES = {'HeavyCharge': (0.0, 0.20, 0.35, 0.50, 0.65, 1.00, 1.40, 2.00),
         'HeavyRelease': (0.075, 0.15, 0.40, 0.60, 0.80, 1.00),
         'Slash1': (0.10, 0.35, 0.65, 0.85)}
FPS = 480.0


def axial(delta, no_roll, axis):
    relative = delta @ no_roll.inverted()
    vector = Vector((relative.x, relative.y, relative.z))
    angle = 2.0 * math.atan2(vector.dot(axis), relative.w)
    return math.degrees((angle + math.pi) % (2.0 * math.pi) - math.pi)


def shoulder_metric(pose, rest):
    clav, child, tail = 'clavicle_l', st.UP, st.LO
    axis = (pose[tail].translation - pose[child].translation).normalized()
    rest_child = (rest[tail].translation - rest[child].translation).normalized()
    parent_delta = pose[clav].to_quaternion() @ rest[clav].to_quaternion().inverted()
    bone_delta = pose[child].to_quaternion() @ rest[child].to_quaternion().inverted()
    no_roll = (parent_delta @ rest_child).rotation_difference(axis) @ parent_delta
    return axial(bone_delta, no_roll, axis)


table = {}
for label, path in BLENDS.items():
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    rig = bpy.data.objects['SK_RuneSword_Rig']
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    rows = {}
    for clip, times in TIMES.items():
        action = bpy.data.actions['A_RuneSword_' + clip]
        rig.animation_data.action = action
        rig.animation_data.action_slot = action.slots[0]
        for t in times:
            scene.frame_set(int(round(t * FPS)))
            bpy.context.view_layer.update()
            pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
            delta = pose[st.UP].to_quaternion() @ rest[st.UP].to_quaternion().inverted()
            rest_axis = (rest[st.LO].translation - rest[st.UP].translation).normalized()
            pose_axis = (pose[st.LO].translation - pose[st.UP].translation).normalized()
            rows['%s %.3f' % (clip, t)] = {
                'elbow_deg': st.elbow_roll(pose, rest),
                'shoulder_deg': shoulder_metric(pose, rest),
                'humerus_local_deg': math.degrees(2 * math.atan2(
                    math.sqrt(rig.pose.bones[st.UP].rotation_quaternion.x ** 2
                              + rig.pose.bones[st.UP].rotation_quaternion.y ** 2
                              + rig.pose.bones[st.UP].rotation_quaternion.z ** 2),
                    abs(rig.pose.bones[st.UP].rotation_quaternion.w))),
                'humerus_axis_error_deg': math.degrees((delta @ rest_axis).angle(pose_axis)),
            }
    table[label] = rows

(P / 'shoulder_report.json').write_text(json.dumps(table, indent=2), encoding='utf-8')
print('%-22s %12s %12s %14s %14s' % ('clip time', 'elbow before', 'elbow after',
                                     'shoulder before', 'shoulder after'))
for key in table['authored']:
    a, b = table['authored'][key], table['v44'][key]
    print('%-22s %12.1f %12.1f %14.1f %14.1f'
          % (key, a['elbow_deg'], b['elbow_deg'], a['shoulder_deg'], b['shoulder_deg']))
print('REPORT_SHOULDER_DONE')
