"""M07 V17 anatomical hip/knee/ankle chain on the unmodified V11 bind.

The V15 whole-body stride, support trajectory and rhythm remain the source.
Only the two locomotion leg chains are reauthored. The original Meshy knee
centres point behind the hips in the reference; its arbitrary Blender bone
axes must not be treated as anatomical hinge axes. Signed flexion crosses
that reference bend without turning the femur/tibia through an axial flip.
No UE, rendering, screenshots or game tests are launched by this producer.
"""
from pathlib import Path
import copy
import json
import math
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'LegJointsV17/Motion'
MASTER = ROOT/'MotionRecoveryV15/LocomotionDeath/M07_Original_LocomotionDeath_V15.blend'
SOURCE_MANIFEST = ROOT/'MotionRecoveryV15/LocomotionDeath/motion_manifest_v15.json'
FPS = 30
UP, RIGHT, FORWARD = Vector((0., 0., 1.)), Vector((1., 0., 0.)), Vector((0., -1., 0.))
sys.path.insert(0, str(Path(__file__).parent))
import author_motion_v04 as motion
import author_running_v12 as running
import author_locomotion_death_v15 as v15


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def degrees(q):
    return math.degrees(2.*math.acos(min(1., abs(q.normalized().w))))


def axial_twist(q, axis):
    q = q.normalized()
    if q.w < 0.:
        q.negate()
    value = 2.*math.atan2(Vector((q.x, q.y, q.z)).dot(axis.normalized()), q.w)
    return math.degrees((value+math.pi) % (2.*math.pi)-math.pi)


def hinge_data(rest, side):
    hip, knee, ankle = (rest[n+'_'+side].translation.copy() for n in ('thigh', 'calf', 'foot'))
    upper, lower = knee-hip, ankle-knee
    u, l = upper.normalized(), lower.normalized()
    hinge = u.cross(l).normalized()
    # Both sides share the positive anatomical lateral axis. Rest flexion is
    # negative in this source; the human forward bend is positive. Keeping
    # this convention is what avoids the V12 reversed-normal 180-degree roll.
    if hinge.dot(RIGHT) < 0.:
        hinge.negate()
    signed_rest_flexion = math.atan2(hinge.dot(u.cross(l)), u.dot(l))
    return {'hip': hip, 'knee': knee, 'ankle': ankle, 'u': u, 'l': l,
            'upper_length': upper.length, 'lower_length': lower.length,
            'hinge': hinge, 'rest_flexion': signed_rest_flexion,
            'upper_frame': motion.anatomical_frame(u, hinge)}


def cache_action(rig, action, count, ordered):
    motion.activate(rig, action)
    frames = []
    for i in range(count):
        bpy.context.scene.frame_set(i+1)
        bpy.context.view_layer.update()
        frames.append({p.name: p.matrix.copy() for p in ordered})
    return frames


def joint_summary(rest, frames, data):
    result = {}
    for side in ('l', 'r'):
        d = data[side]
        flex, thigh_twist, calf_twist, hinge_error, ankle_roll, knee_axial, knee_off_hinge = [], [], [], [], [], [], []
        positions = []
        for index, pose in enumerate(frames):
            hip, knee, ankle = (pose[n+'_'+side].translation for n in ('thigh', 'calf', 'foot'))
            u, l = (knee-hip).normalized(), (ankle-knee).normalized()
            actual_hinge = u.cross(l).normalized()
            if actual_hinge.dot(RIGHT) < 0.:
                actual_hinge.negate()
            du = pose['thigh_'+side].to_quaternion()@rest['thigh_'+side].to_quaternion().inverted()
            dl = pose['calf_'+side].to_quaternion()@rest['calf_'+side].to_quaternion().inverted()
            thigh_twist.append(axial_twist(d['u'].rotation_difference(u).inverted()@du, d['u']))
            calf_twist.append(axial_twist(d['l'].rotation_difference(l).inverted()@dl, d['l']))
            hinge_error.append(math.degrees((du@d['hinge']).angle(actual_hinge)))
            flex.append(math.degrees(math.atan2(actual_hinge.dot(u.cross(l)), u.dot(l))))
            knee_delta = du.inverted()@dl
            intended_hinge_delta = Quaternion(d['hinge'], math.radians(flex[-1])-d['rest_flexion'])
            residual_knee = intended_hinge_delta.inverted()@knee_delta
            knee_axial.append(axial_twist(residual_knee, d['l']))
            knee_off_hinge.append(degrees(residual_knee))
            # Signed lateral foot roll is measured from actual ankle/ball
            # geometry, not the differently rolled L/R source bone matrices.
            ball = pose['ball_'+side].translation
            foot_direction = (ball-ankle).normalized()
            delta_foot = pose['foot_'+side].to_quaternion()@rest['foot_'+side].to_quaternion().inverted()
            support_lateral = delta_foot@RIGHT
            ankle_roll.append(math.degrees(math.atan2(support_lateral.z, max(.00001, abs(support_lateral.x)))))
            positions.append({'frame': index+1, 'seconds': index/FPS,
                'hip_cm': list(hip), 'knee_cm': list(knee), 'ankle_cm': list(ankle),
                'knee_flexion_degrees': flex[-1], 'thigh_axial_degrees': thigh_twist[-1],
                'calf_axial_degrees': calf_twist[-1], 'femur_hinge_error_degrees': hinge_error[-1],
                'knee_joint_axial_residual_degrees': knee_axial[-1],
                'knee_joint_off_hinge_rotation_degrees': knee_off_hinge[-1],
                'foot_roll_degrees': ankle_roll[-1]})
        result[side] = {
            'knee_flexion_range_degrees': [min(flex), max(flex)],
            'thigh_axial_range_degrees': [min(thigh_twist), max(thigh_twist)],
            'calf_axial_range_degrees': [min(calf_twist), max(calf_twist)],
            'max_femur_hinge_misalignment_degrees': max(hinge_error),
            'knee_joint_axial_residual_range_degrees': [min(knee_axial), max(knee_axial)],
            'max_knee_joint_off_hinge_rotation_degrees': max(knee_off_hinge),
            'ankle_roll_range_degrees': [min(ankle_roll), max(ankle_roll)],
            'requested_source_joint_samples': positions}
    return result


def solve_chain(rest, local, data, source, side, phase, stance):
    d = data[side]
    hip = source['thigh_'+side].translation.copy()
    goal = source['foot_'+side].translation.copy()
    axis = (goal-hip).normalized()
    # Reach limits keep the knee circle away from its singular straight pose,
    # rather than attenuating the requested stride or recovery lift.
    min_flex, max_flex = math.radians(10.), math.radians(145.)
    l1, l2 = d['upper_length'], d['lower_length']
    maximum = math.sqrt(l1*l1+l2*l2+2.*l1*l2*math.cos(min_flex))
    minimum = math.sqrt(l1*l1+l2*l2+2.*l1*l2*math.cos(max_flex))
    distance = min(maximum, max(minimum, (goal-hip).length))
    ankle = hip+axis*distance
    pelvis_delta = source['pelvis'].to_quaternion()@rest['pelvis'].to_quaternion().inverted()
    # Only a bounded pelvis yaw steers the hinge plane. Pelvis roll/pitch
    # causes hip abduction and flexion; it must not roll the knee axis.
    body_forward = pelvis_delta@FORWARD
    body_forward.z = 0.
    body_forward.normalize()
    yaw = math.atan2(body_forward.x, -body_forward.y)
    yaw = max(math.radians(-12.), min(math.radians(12.), yaw))
    front = Quaternion(UP, yaw)@FORWARD
    pole = front-axis*front.dot(axis)
    if pole.length < .001:
        pole = FORWARD-axis*FORWARD.dot(axis)
    pole.normalize()
    along = (l1*l1-l2*l2+distance*distance)/(2.*distance)
    height = math.sqrt(max(0., l1*l1-along*along))
    def circle_pose(pole_angle):
        candidate = Quaternion(axis, pole_angle)@pole
        k = hip+axis*along+candidate*height
        u, l = (k-hip).normalized(), (ankle-k).normalized()
        h = u.cross(l).normalized()
        if h.dot(RIGHT) < 0.:
            h.negate()
        du = (motion.anatomical_frame(u, h)@d['upper_frame'].transposed()).to_quaternion()
        twist = axial_twist(d['u'].rotation_difference(u).inverted()@du, d['u'])
        return k, u, l, h, du, twist

    solved = circle_pose(0.)
    # A joint limit rotates the knee circle, never shortens the support
    # stride. Its scalar root stays on the same forward-knee branch; no
    # history-dependent per-frame normal choice is made at the loop seam.
    hip_limit = 24.
    if abs(solved[-1]) > hip_limit:
        boundary = math.copysign(hip_limit, solved[-1])
        probes = [(math.radians(a), circle_pose(math.radians(a))) for a in range(-24, 25, 2)]
        crossings = [(a,x,b,y) for (a,x),(b,y) in zip(probes, probes[1:])
            if (x[-1]-boundary)*(y[-1]-boundary) <= 0.]
        if crossings:
            a,x,b,y = min(crossings, key=lambda item: min(abs(item[0]),abs(item[2])))
            for _ in range(16):
                mid = (a+b)*.5
                current = circle_pose(mid)
                if (x[-1]-boundary)*(current[-1]-boundary) <= 0.:
                    b,y = mid,current
                else:
                    a,x = mid,current
            solved = circle_pose((a+b)*.5)
        else:
            solved = min((v for _,v in probes), key=lambda item: abs(item[-1]))
    knee, upper, lower, hinge, upper_delta, _ = solved
    # One explicit signed hinge drives the entire thigh/calf orientation.
    # The reference's backward bend is crossed by flexion, never by an
    # independent minimum-swing tibia roll or a reversed normal frame.
    signed_flexion = math.atan2(hinge.dot(upper.cross(lower)), upper.dot(lower))
    lower_delta = upper_delta@Quaternion(d['hinge'], signed_flexion-d['rest_flexion'])
    thigh_q = upper_delta@rest['thigh_'+side].to_quaternion()
    calf_q = lower_delta@rest['calf_'+side].to_quaternion()
    # The old navigation-matched support ankle and independent pitch/ball
    # frame remain. They contain no global toe yaw/roll and avoid dragging
    # the original long foot into the tibia's arbitrary rolled bone axes.
    foot_q = source['foot_'+side].to_quaternion().copy()
    ball_q = source['ball_'+side].to_quaternion().copy()
    return {
        'thigh_'+side: Matrix.LocRotScale(hip, thigh_q, Vector((1., 1., 1.))),
        'calf_'+side: Matrix.LocRotScale(knee, calf_q, Vector((1., 1., 1.))),
        'foot_'+side: Matrix.LocRotScale(ankle, foot_q, Vector((1., 1., 1.))),
        'ball_'+side: Matrix.LocRotScale(Matrix.LocRotScale(ankle, foot_q, Vector((1., 1., 1.)))@local['ball_'+side].translation,
            ball_q, Vector((1., 1., 1.)))
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = json.loads(SOURCE_MANIFEST.read_text(encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.data.bones.get('gill_01_00'))
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    local = {b.name: b.parent.matrix_local.inverted()@b.matrix_local if b.parent else b.matrix_local.copy() for b in rig.data.bones}
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    hidden = {o.name: o.hide_viewport for o in bpy.data.objects if o.type == 'MESH'}
    for name in hidden:
        bpy.data.objects[name].hide_viewport = True
    data = {s: hinge_data(rest, s) for s in ('l', 'r')}
    cache = {role: cache_action(rig, bpy.data.actions[source['clips'][role]['action']], source['clips'][role]['frames'], ordered)
             for role in ('SlowWalk', 'Chase')}
    source_summary = {role: joint_summary(rest, frames, data) for role, frames in cache.items()}
    points = {side: {'hip_cm': list(d['hip']), 'knee_cm': list(d['knee']), 'ankle_cm': list(d['ankle']),
        'upper_length_cm': d['upper_length'], 'lower_length_cm': d['lower_length'],
        'reference_positive_hinge_axis': list(d['hinge']),
        'signed_reference_knee_flexion_degrees': math.degrees(d['rest_flexion']),
        'source_bone_local_y_is_anatomical_segment_axis': False} for side, d in data.items()}
    write(OUT/'source_leg_joint_diagnosis_v17.json', {'source': str(MASTER), 'scope': 'User-requested source hip/knee/ankle localization and numeric articulation diagnosis only',
        'anatomical_joint_reference': points, 'clips': source_summary, 'runtime_tested': False, 'rendered': False})
    print('M07_V17_SOURCE_JOINT_DIAGNOSIS '+json.dumps({'reference': points,
        'clips': {r: {s: {k:v for k,v in values.items() if k != 'requested_source_joint_samples'} for s,values in sides.items()} for r,sides in source_summary.items()}}), flush=True)
    if '--source-only' in sys.argv:
        return
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.
    scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', .01
    manifest = {'revision': 'LegJointsV17Motion', 'source_master': str(MASTER),
        'source': str(OUT/'M07_Original_LegJoints_V17.blend'), 'fps': FPS,
        'reference_skeleton': source['reference_skeleton'], 'bone_names': list(rest),
        'bone_reference': {n: motion.rows(m) for n,m in rest.items()}, 'rig_object_matrix_world': motion.rows(rig.matrix_world),
        'reference_pose_modified': False, 'geometry_modified': False, 'weights_modified': False,
        'root_motion': False, 'clips': {}, 'anatomical_joint_reference': points,
        'source_diagnosis': str(OUT/'source_leg_joint_diagnosis_v17.json'),
        'joint_constraints': {'knee_flexion_degrees': [10.,145.], 'knee_steering_yaw_degrees': [-12.,12.],
            'hip_extra_axial_twist_limit_degrees': [-24.,24.],
            'knee_circle_constraint_correction_limit_degrees': [-24.,24.],
            'knee_axial_joint_rotation_degrees': 0., 'reference_hinge_sign': 'Positive anatomical lateral axis for both sides; signed backward source rest bend is negative',
            'ankle_support_frame': 'V15 original independent foot/ball pitch; no knee roll inheritance',
            'nonleg_policy': 'Exact V15 local whole-body, torso, opposed arm, hands and gill choreography; no gait speed/cycle reduction'},
        'runtime_tested': False, 'rendered': False, 'tested': False, 'visual_accepted': False,
        'ue_imported': False, 'user_review_pending': True}
    actions = {}
    for role in ('SlowWalk', 'Chase'):
        entry = copy.deepcopy(source['clips'][role])
        count, stance = entry['frames'], entry['stance_fraction']
        action = bpy.data.actions.new('A_M07_'+role+'_LegJointsV17')
        action.use_fake_user = True
        motion.activate(rig, action)
        previous, targets = {}, []
        for i, old in enumerate(cache[role]):
            frame, u = i+1, i/(count-1)
            scene.frame_set(frame)
            target = {n:m.copy() for n,m in old.items()}
            for side, offset in (('l',0.),('r',.5)):
                target.update(solve_chain(rest, local, data, old, side, (u+offset)%1., stance))
            if i == count-1:
                target = {n:m.copy() for n,m in targets[0].items()}
            targets.append(target)
            running.insert_frame(rig, target, rest, ordered, frame, previous)
        scene.frame_set(0)
        for p in ordered:
            p.matrix_basis = Matrix.Identity(4)
            for channel in ('location', 'rotation_quaternion', 'scale'):
                p.keyframe_insert(data_path=channel, frame=0, group=p.name)
        for curve in running.curves(action):
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        file = OUT/('A_M07_'+role+'.fbx')
        v15.export(rig, action, file, count)
        # Production metadata is derived directly from the matrices authored
        # above; this is not a separate runtime/render/test invocation.
        summary = joint_summary(rest, targets, data)
        entry.update(action=action.name, file=str(file), asset='/Game/Monsters/BlindSupplicantM07/AnimationsLegJointsV17/A_M07_'+role,
            reference_only_blender_frame=0, exported_blender_frame_start=1, exported_blender_frame_end=count,
            all_child_locations_zero_except_pelvis=True, bone_tracks=list(rest),
            grounding='V15 original navigation-matched support/recovery trajectory retained; anatomical positive hinge with signed reference flexion and bounded pelvis-yaw steering',
            child_frame_policy='One femur hinge frame; tibia is the explicit scalar hinge flexion from that femur; unmodified V11 child offsets and unit scale',
            authored_joint_summary={s:{k:v for k,v in a.items() if k != 'requested_source_joint_samples'} for s,a in summary.items()})
        manifest['clips'][role], actions[role] = entry, action
        write(OUT/('authored_'+role.lower()+'_joint_record_v17.json'), {'source_action': source['clips'][role]['action'],
            'authored_action': action.name, 'scope': 'Direct authored production joint data', 'joints': summary,
            'runtime_tested': False, 'rendered': False})
        print('M07_V17_LEG_CLIP_EXPORTED '+role+' '+json.dumps(entry['authored_joint_summary']), flush=True)
    for name, value in hidden.items():
        bpy.data.objects[name].hide_viewport = value
    motion.activate(rig, actions['Chase'])
    scene.frame_start, scene.frame_end = 1, manifest['clips']['Chase']['frames']
    scene.frame_set(0)
    rig['leg_joint_revision'] = 'V17 exact original V11 bind; signed anatomical knee flexion without reference-normal reversal or independently rolled tibia'
    bpy.ops.wm.save_as_mainfile(filepath=manifest['source'], compress=True)
    manifest.update(source_saved=True, animation_fbx_exported=True,
        root_cause='The source bind knees lie behind the hips and source bone local Y axes point vertically instead of along actual hip-knee/ankle segments. V15 independent minimum-swing thigh/calf transports do not constrain an anatomical shared hinge; femur hinge misalignment and axial tibia rotation persist during the forward-bending stance/recovery cycle. V17 resolves signed knee flexion on a consistent lateral hinge frame while retaining all source joint lengths and gait trajectories.',
        preservation='Only two new locomotion action datablocks. Original83boneV11 matrices, V16 mesh/arms/sweeps and V15 death/casting remain unchanged; locally corrected V17 skin can use the same bind.')
    write(OUT/'leg_motion_manifest_v17.json', manifest)
    print('M07_V17_LEG_JOINT_MASTER_SAVED '+manifest['source'], flush=True)


if __name__ == '__main__':
    main()
