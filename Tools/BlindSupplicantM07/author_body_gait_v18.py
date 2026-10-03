"""M07 V18 locomotion: support-led body rhythm on the unchanged original rig.

This producer owns only BodyMotionV18/Move. Source investigation is part of
the requested gait repair, and no runtime, rendering or game test is run.
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
OUT = ROOT/'BodyMotionV18/Move'
MASTER = ROOT/'LegJointsV17/Motion/M07_Original_LegJoints_V17.blend'
SOURCE_MANIFEST = ROOT/'LegJointsV17/Motion/leg_motion_manifest_v17.json'
SKIN_MASTER = ROOT/'LegJointsV17/Skin/M07_Original_LegJoints_V17.blend'
FPS = 30
UP, RIGHT, FORWARD = Vector((0., 0., 1.)), Vector((1., 0., 0.)), Vector((0., -1., 0.))
sys.path.insert(0, str(Path(__file__).parent))
import author_motion_v04 as motion
import author_running_v12 as running
import author_locomotion_death_v15 as v15
import author_leg_joint_motion_v17 as v17

CONFIG = {
    'SlowWalk': {'intervals': 36, 'speed_cm_s': 160., 'stance_fraction': .61,
        'foot_lift_cm': 12., 'crouch_cm': 7., 'pelvis_bounce_cm': 1.9,
        'pelvis_sway_cm': 3.0, 'pelvis_yaw_deg': 5.2, 'pelvis_roll_deg': 2.0,
        'pelvis_lean_deg': 1.4, 'chest_lean_deg': 5.1, 'chest_yaw_deg': 4.2,
        'upperarm_range_deg': [-12., 45.], 'elbow_range_deg': [31., 45.],
        'arm_abduction_deg': 14., 'push_off_pitch_deg': 21., 'recovery_pitch_deg': -11.},
    'Chase': {'intervals': 24, 'speed_cm_s': 360., 'stance_fraction': .38,
        'foot_lift_cm': 34., 'crouch_cm': 8., 'pelvis_bounce_cm': 2.7,
        'pelvis_sway_cm': 1.7, 'pelvis_yaw_deg': 6.7, 'pelvis_roll_deg': 2.0,
        'pelvis_lean_deg': 3.2, 'chest_lean_deg': 12.1, 'chest_yaw_deg': 6.0,
        'upperarm_range_deg': [-12., 62.], 'elbow_range_deg': [78., 88.],
        'arm_abduction_deg': 17., 'push_off_pitch_deg': 26., 'recovery_pitch_deg': -14.},
}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def rot(axis, degrees):
    return Quaternion(axis, math.radians(degrees))


def motion_statistics(rest, frames):
    result = {'pelvis_xyz_range_cm': [[min(f['pelvis'].translation[k] for f in frames),
                                     max(f['pelvis'].translation[k] for f in frames)] for k in range(3)],
              'spine05_forward_lean_range_deg': [], 'feet': {}, 'arms': {}}
    lean = []
    for f in frames:
        q = f['spine_05'].to_quaternion()@rest['spine_05'].to_quaternion().inverted()
        axis = q@UP
        lean.append(math.degrees(math.atan2(-axis.y, axis.z)))
    result['spine05_forward_lean_range_deg'] = [min(lean), max(lean)]
    for side in ('l', 'r'):
        rows, swing, bend = [], [], []
        for i, f in enumerate(frames):
            hip, knee, ankle, toe = (f[n+'_'+side].translation for n in ('thigh', 'calf', 'foot', 'ball'))
            u, l = (knee-hip).normalized(), (ankle-knee).normalized()
            torso = f['spine_05'].to_quaternion()@rest['spine_05'].to_quaternion().inverted()
            upper = torso.inverted()@(f['lowerarm_'+side].translation-f['upperarm_'+side].translation).normalized()
            fore = (f['hand_'+side].translation-f['lowerarm_'+side].translation).normalized()
            real_upper = (f['lowerarm_'+side].translation-f['upperarm_'+side].translation).normalized()
            swing.append(math.degrees(math.atan2(-upper.y, -upper.z)))
            bend.append(math.degrees(real_upper.angle(fore)))
            rows.append({'frame': i+1, 'seconds': i/FPS, 'hip_cm': list(hip), 'knee_cm': list(knee),
                'ankle_cm': list(ankle), 'toe_cm': list(toe), 'knee_flex_deg': math.degrees(u.angle(l)),
                'knee_lateral_offset_from_hip_cm': knee.x-hip.x,
                'ankle_height_cm': ankle.z, 'toe_height_cm': toe.z})
        result['feet'][side] = {'toe_xyz_range_cm': [[min(r['toe_cm'][k] for r in rows), max(r['toe_cm'][k] for r in rows)] for k in range(3)],
            'knee_flexion_range_deg': [min(r['knee_flex_deg'] for r in rows), max(r['knee_flex_deg'] for r in rows)],
            'knee_lateral_offset_cm': [min(r['knee_lateral_offset_from_hip_cm'] for r in rows), max(r['knee_lateral_offset_from_hip_cm'] for r in rows)],
            'joint_samples': rows}
        result['arms'][side] = {'upperarm_sagittal_range_deg': [min(swing), max(swing)], 'elbow_range_deg': [min(bend), max(bend)]}
    return result


def body_target(rest, local, ordered, u, role):
    """One support clock replaces stacked pelvis/body oscillations."""
    c = CONFIG[role]
    theta = 2.*math.pi*u
    run = role == 'Chase'
    hip_yaw = -c['pelvis_yaw_deg']*math.cos(theta-.05)
    chest_yaw = c['chest_yaw_deg']*math.cos(theta-.12)
    hip_roll = c['pelvis_roll_deg']*math.sin(theta-.15)
    position = rest['pelvis'].translation.copy()
    position.x += c['pelvis_sway_cm']*math.sin(theta-.10)
    position.y -= 1.1 if run else .5
    # Walk rises over mid-stance. Run compresses over mid-stance, then rises
    # through flight; these are different support mechanics, not one bob
    # layered twice over a pre-crouched source pelvis.
    support_midpoint = c['stance_fraction']*.5
    bounce_phase = u-support_midpoint if run else u
    position.z += -c['crouch_cm']-c['pelvis_bounce_cm']*math.cos(4.*math.pi*bounce_phase)
    pelvis_pitch = c['pelvis_lean_deg']+.35*math.sin(2.*theta-.16)
    chest_pitch = c['chest_lean_deg']+(.85 if run else .45)*math.sin(2.*theta-.28)
    target = {}
    for pose in ordered:
        name = pose.name
        point, q = v15.inherited(target, rest, local, pose)
        if name == 'pelvis':
            point = position
            q = rot(RIGHT, pelvis_pitch)@rot(UP, hip_yaw)@rot(FORWARD, hip_roll)@rest[name].to_quaternion()
        elif name.startswith('spine_'):
            # Five local joints share the requested total chest opposition;
            # each contribution is small and their sum has a fixed meaning.
            q = rot(UP, (chest_yaw-hip_yaw)*.2)@rot(RIGHT, (chest_pitch-pelvis_pitch)*.2)@rot(FORWARD, -hip_roll*.14)@q
        elif name.startswith('clavicle_'):
            sign = 1. if name.endswith('_l') else -1.
            q = rot(UP, sign*(1.7 if run else 1.1)*math.sin(theta-.10))@rot(FORWARD, sign*.75*math.cos(theta))@q
        elif name.startswith(('neck_', 'head')):
            q = rot(UP, -chest_yaw*.27)@rot(FORWARD, -hip_roll*.10)@rot(RIGHT, -.35 if run else -.2)@q
        target[name] = Matrix.LocRotScale(point, q, Vector((1., 1., 1.)))
    return target


def foot_path(rest, side, phase, c, stride):
    """Place the ANKLE, rather than the toe, around its hip support line.

    Original ankles stand about 15 cm behind the hips and the forefeet lie
    further in front. Centering a new stride around those uncorrected toes
    created an excessively long rear reach and forced pelvis settling.
    A constant path-origin correction keeps that anatomical foot intact.
    """
    stance = c['stance_fraction']
    support = stride*stance
    front, back = support*.5, -support*.5
    toe = rest['ball_'+side].translation.copy()
    hip, ankle = rest['thigh_'+side].translation, rest['foot_'+side].translation
    toe.y -= ankle.y-hip.y
    toe.x += hip.x-ankle.x
    if phase < stance:
        progress = phase/stance
        forward, lift = front-stride*phase, 0.
        pitch = -2.*(1.-motion.smooth(progress/.18))
        pitch += c['push_off_pitch_deg']*motion.smooth((progress-.62)/.38)
        ball_pitch = -min(16., pitch*.70)
        contact = 1.
    else:
        progress = (phase-stance)/(1.-stance)
        tangent = -stride*(1.-stance)
        # A long cubic return overshoots the upcoming contact by ~12 cm in
        # the source run, driving the leg straight and abruptly lowering the
        # whole pelvis shortly before the loop boundary. Bound the braking
        # and contact-preparation lobes while retaining the exact support
        # velocity at both ends. The integrated smooth velocity has C2 joins.
        brake = .065 if c['speed_cm_s'] > 200. else .10
        overshoot = -tangent*brake*.5
        if progress < brake:
            q = progress/brake
            forward = back+tangent*brake*(q-q**3+.5*q**4)
        elif progress > 1.-brake:
            q = (progress-(1.-brake))/brake
            forward = front+overshoot+tangent*brake*(q**3-.5*q**4)
        else:
            q = (progress-brake)/(1.-2.*brake)
            blend = q**3*(10.+q*(-15.+6.*q))
            forward = back-overshoot+(front-back+2.*overshoot)*blend
        lift = c['foot_lift_cm']*math.sin(math.pi*progress)**1.65
        pitch = c['push_off_pitch_deg']*(1.-motion.smooth(progress/.26))
        pitch += c['recovery_pitch_deg']*math.sin(math.pi*progress)**1.2
        pitch -= 2.*motion.smooth((progress-.78)/.22)
        ball_pitch = -7.*math.sin(math.pi*progress)
        toe.x += (1. if side == 'l' else -1.)*.8*math.sin(math.pi*progress)**2
        contact = 0.
    toe += FORWARD*forward+UP*lift
    foot_q = rot(RIGHT, pitch)@rest['foot_'+side].to_quaternion()
    ankle_to_ball = rest['foot_'+side].to_quaternion().inverted()@(rest['ball_'+side].translation-rest['foot_'+side].translation)
    goal = toe-foot_q@ankle_to_ball
    ball_q = rot(RIGHT, ball_pitch)@rot(RIGHT, pitch)@rest['ball_'+side].to_quaternion()
    return goal, foot_q, ball_q, contact


def install_feet(target, rest, local, ordered, data, u, role):
    c = CONFIG[role]
    stride = c['speed_cm_s']*c['intervals']/FPS
    goals, settling = {}, 0.
    for side, offset in (('l', 0.), ('r', .5)):
        goals[side] = foot_path(rest, side, (u+offset)%1., c, stride)
        goal = goals[side][0]
        hip = target['thigh_'+side].translation
        d = data[side]
        reach = math.sqrt(d['upper_length']**2+d['lower_length']**2+
            2.*d['upper_length']*d['lower_length']*math.cos(math.radians(10.)))
        horizontal = (goal.x-hip.x)**2+(goal.y-hip.y)**2
        available = math.sqrt(max(0., reach*reach-horizontal))
        settling = max(settling, hip.z-goal.z-available)
    if settling > 0.:
        for m in target.values():
            m.translation.z -= settling
    for side, offset in (('l', 0.), ('r', .5)):
        goal, foot_q, ball_q, _ = goals[side]
        source_pose = dict(target)
        source_pose['foot_'+side] = Matrix.LocRotScale(goal, foot_q, Vector((1., 1., 1.)))
        source_pose['ball_'+side] = Matrix.LocRotScale(goal, ball_q, Vector((1., 1., 1.)))
        # Reuse the V17 single signed anatomical hinge. Neither bone.local Y
        # nor independent minimum-swing tibia rotation is used for the knee.
        target.update(v17.solve_chain(rest, local, data, source_pose, side, (u+offset)%1., c['stance_fraction']))
    return {s: goals[s][3] for s in goals}, settling


def install_arms(target, rest, local, ordered, old, u, role):
    c = CONFIG[role]
    theta = 2.*math.pi*u
    chest = target['spine_05'].to_quaternion()@rest['spine_05'].to_quaternion().inverted()
    # Body pitch is not copied into the hanging arm frame: that caused the
    # already rear-swinging humerus to move deeper into the shoulder gills.
    # Chest yaw/weight roll still steer the opposed sagittal arm arcs.
    body_forward = chest@FORWARD
    yaw = math.degrees(math.atan2(body_forward.x, -body_forward.y))
    arm_frame = rot(UP, yaw)@rot(FORWARD, c['pelvis_roll_deg']*.18*math.sin(theta-.15))
    deltas = {}
    for side, offset, sign in (('l', 0., 1.), ('r', .5, -1.)):
        phase = (u+offset)%1.
        wave = -math.cos(2.*math.pi*phase-.06)
        lo, hi = c['upperarm_range_deg']
        swing = math.radians((lo+hi)*.5+(hi-lo)*.5*wave)
        elbow_lo, elbow_hi = c['elbow_range_deg']
        elbow_wave = (.5-.5*wave) if role == 'Chase' else (.5+.5*wave)
        bend = math.radians(elbow_lo+(elbow_hi-elbow_lo)*elbow_wave)
        abduction = math.radians(c['arm_abduction_deg'])
        sagittal = Vector((0., -math.sin(swing), -math.cos(swing)))
        upper = arm_frame@(sagittal*math.cos(abduction)+RIGHT*(sign*math.sin(abduction)))
        upper.normalize()
        flex = arm_frame@FORWARD
        flex -= upper*flex.dot(upper)
        flex.normalize()
        lower = (upper*math.cos(bend)+flex*math.sin(bend)).normalized()
        original_u = (rest['lowerarm_'+side].translation-rest['upperarm_'+side].translation).normalized()
        original_l = (rest['hand_'+side].translation-rest['lowerarm_'+side].translation).normalized()
        du = (chest@original_u).rotation_difference(upper)@chest
        dl = (du@original_l).rotation_difference(lower)@du
        deltas[side] = du, dl
    for pose in ordered:
        name = pose.name
        if not name.startswith(('upperarm_', 'lowerarm_', 'hand_', 'thumb_', 'index_', 'middle_', 'ring_', 'pinky_', 'gill_')):
            continue
        parent = pose.parent.name
        point, q = v15.inherited(target, rest, local, pose)
        if name.startswith('upperarm_'):
            q = deltas[name[-1]][0]@rest[name].to_quaternion()
        elif name.startswith('lowerarm_'):
            q = deltas[name[-1]][1]@rest[name].to_quaternion()
        elif name.startswith('hand_'):
            q = deltas[name[-1]][1]@rest[name].to_quaternion()
            # Only modest anatomical wrist lag; the forearm leads the hand.
            q = rot(deltas[name[-1]][1]@RIGHT, 1.5*math.sin(theta+(0. if name.endswith('_l') else math.pi)-.15))@q
        else:
            # Preserve the actual V17 finger articulation and original gill
            # local breathing curves, rather than curling around arbitrary
            # source bone.local Y axes or changing attachment offsets.
            old_local = old[parent].inverted()@old[name]
            q = target[parent].to_quaternion()@old_local.to_quaternion()
        target[name] = Matrix.LocRotScale(point, q, Vector((1., 1., 1.)))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = json.loads(SOURCE_MANIFEST.read_text(encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.data.bones.get('gill_01_00'))
    rig.data.pose_position = 'POSE'
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    local = {b.name: b.parent.matrix_local.inverted()@b.matrix_local if b.parent else b.matrix_local.copy() for b in rig.data.bones}
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    visibility = {o.name: o.hide_viewport for o in bpy.data.objects if o.type == 'MESH'}
    for n in visibility:
        bpy.data.objects[n].hide_viewport = True
    cache = {role: v17.cache_action(rig, bpy.data.actions[source['clips'][role]['action']], source['clips'][role]['frames'], ordered)
             for role in ('SlowWalk', 'Chase')}
    diagnosis = {role: motion_statistics(rest, frames) for role, frames in cache.items()}
    write(OUT/'source_gait_diagnosis_v18.json', {'source': str(MASTER),
        'scope': 'User-requested source gait articulation and body/support rhythm investigation',
        'clips': diagnosis, 'runtime_tested': False, 'rendered': False})
    print('M07_V18_SOURCE_GAIT '+json.dumps({role: {**value, 'feet': {side: {k:v for k,v in foot.items() if k != 'joint_samples'} for side, foot in value['feet'].items()}} for role,value in diagnosis.items()}), flush=True)
    if '--source-only' in sys.argv:
        return
    # The editable deliverable contains the actual current V17 body/skin,
    # including V16 corrected arms. Only two new action datablocks are added.
    bpy.ops.wm.open_mainfile(filepath=str(SKIN_MASTER))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.data.bones.get('gill_01_00'))
    # Skin authoring leaves this rig in REST. FBX baking must evaluate the
    # action, otherwise every exported frame becomes the reference T pose.
    rig.data.pose_position = 'POSE'
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    local = {b.name: b.parent.matrix_local.inverted()@b.matrix_local if b.parent else b.matrix_local.copy() for b in rig.data.bones}
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    visibility = {o.name: o.hide_viewport for o in bpy.data.objects if o.type == 'MESH'}
    for name in visibility:
        bpy.data.objects[name].hide_viewport = True
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.
    scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', .01
    data = {s: v17.hinge_data(rest, s) for s in ('l', 'r')}
    manifest = {'revision': 'BodyMotionV18Move', 'source_master': str(MASTER),
        'mesh_skin_master': str(SKIN_MASTER), 'source': str(OUT/'M07_Original_BodyGait_V18.blend'),
        'source_diagnosis': str(OUT/'source_gait_diagnosis_v18.json'), 'fps': FPS,
        'reference_skeleton': source['reference_skeleton'], 'bone_names': list(rest),
        'bone_reference': {n: motion.rows(m) for n,m in rest.items()},
        'rig_object_matrix_world': motion.rows(rig.matrix_world),
        'reference_pose_modified': False, 'geometry_modified': False, 'weights_modified': False,
        'root_motion': False, 'clips': {}, 'runtime_tested': False, 'rendered': False,
        'animation_export_pose_position': 'POSE',
        'static_reference_export_repaired': True,
        'tested': False, 'visual_accepted': False, 'ue_imported': False,
        'user_review_pending': True,
        'source_causes': [
            'V17 fixed knee roll but deliberately retained the older support/body trajectories. Its walk pelvis moves laterally across 14.14 cm and vertically across 10.73 cm; run height spans 13.53 cm with overlapping inherited and additional body oscillations.',
            'The source toe-centered stride keeps the original ankle 15.72/16.08 cm behind its hip. The rear reach is therefore excessive, requiring additional full-body settling near toe-off and unequal front/rear leg extension.',
            'The source planted foot still translates laterally up to 2 cm while in support, although its forward speed matches capsule travel.',
            'The run lifts the forefoot by 58 cm and flexes the knee to about 136 degrees; the original 48 cm-wide forefoot path and large lateral knee excursion make recovery appear strongly folded and spread.',
            'The source running upper arm swings about 37 degrees backward relative to the leaning chest. Copying chest pitch into that hanging arm frame further places the humerus inside the rear gill space.'
        ],
        'scope': 'Two locomotion actions only; original complete model, V17 leg weights, V16 hand/arm weights and V11 83-bone reference remain unchanged.'}
    actions = {}
    for role in ('SlowWalk', 'Chase'):
        c = CONFIG[role]
        count, duration = c['intervals']+1, c['intervals']/FPS
        action = bpy.data.actions.new('A_M07_'+role+'_BodyGaitV18')
        action.use_fake_user = True
        motion.activate(rig, action)
        previous, targets, contacts, settling = {}, [], {'l': [], 'r': []}, []
        for i in range(count):
            frame, u = i+1, i/c['intervals']
            scene.frame_set(frame)
            target = body_target(rest, local, ordered, u, role)
            contact, settled = install_feet(target, rest, local, ordered, data, u, role)
            old = motion.sample({'samples': cache[role], 'rest': rest}, u)
            install_arms(target, rest, local, ordered, old, u, role)
            if i == count-1:
                target = {n:m.copy() for n,m in targets[0].items()}
                contact = {s: contacts[s][0] for s in contacts}
                settled = settling[0]
            targets.append(target)
            settling.append(settled)
            for side in contacts:
                contacts[side].append(contact[side])
            running.insert_frame(rig, target, rest, ordered, frame, previous)
        scene.frame_set(0)
        for pose in ordered:
            pose.matrix_basis = Matrix.Identity(4)
            for channel in ('location', 'rotation_quaternion', 'scale'):
                pose.keyframe_insert(data_path=channel, frame=0, group=pose.name)
        for curve in running.curves(action):
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        file = OUT/('A_M07_'+role+'.fbx')
        v15.export(rig, action, file, count)
        summary = motion_statistics(rest, targets)
        joints = v17.joint_summary(rest, targets, data)
        # These records describe the authored matrices, not a second export
        # inspection, a runtime simulation or an acceptance test.
        write(OUT/('authored_'+role.lower()+'_body_record_v18.json'), {
            'scope': 'Direct production matrices for the requested gait repair',
            'action': action.name, 'body_and_support': summary,
            'anatomical_leg_hinge': joints, 'pelvis_reach_settling_cm': settling,
            'runtime_tested': False, 'rendered': False})
        entry = {'role': role, 'action': action.name, 'file': str(file),
            'asset': '/Game/Monsters/BlindSupplicantM07/AnimationsBodyMotionV18/A_M07_'+role,
            'fps': FPS, 'frames': count, 'duration': duration, 'duration_seconds': duration,
            'seconds': duration, 'loop': True, 'root_motion': False,
            'speed_cm_s': c['speed_cm_s'], 'expected_speed_cm_s': c['speed_cm_s'],
            'stride_cm': c['speed_cm_s']*duration, 'step_cm': c['speed_cm_s']*duration*.5,
            'cadence_steps_per_minute': 120./duration,
            'rhythm_revision': 'Source slow cycle 1.333 s/90 steps per minute -> 1.2 s/100; source chase .933 s/128.6 -> .8 s/150. Speed remains160/360 cm/s, step lengths96/144 cm remain large; shorter recovery avoids overreaching and improves limb/body coordination.',
            'stance_fraction': c['stance_fraction'], 'flight_phase': role == 'Chase',
            'foot_contact': contacts, 'curves': {'FootContact_l': contacts['l'], 'FootContact_r': contacts['r']},
            'reference_only_blender_frame': 0, 'exported_blender_frame_start': 1,
            'exported_blender_frame_end': count, 'all_child_locations_zero_except_pelvis': True,
            'bone_tracks': list(rest), 'config': copy.deepcopy(c),
            'max_reach_settling_cm': max(settling),
            'arm_leg_phase': 'Contralateral: same-side arm retracts when the foot advances; pelvis and chest counterturn on one shared cycle',
            'support_origin': 'Original ankle support line centered around actual hip; full original foot shape and reference offsets retained',
            'support_lateral_policy': 'Fixed lateral coordinate during stance; only .8 cm outward recovery arc in flight',
            'swing_reach_policy': 'Integrated C2 braking/contact preparation with bounded overshoot; one monotonic quintic return, retaining exact navigation-matched support velocity at both ends',
            'knee_frame': 'Unmodified V17 common signed anatomical hinge and bound hip axial correction, not independent femur/tibia rolls',
            'gill_avoidance': 'Bounded -12 degree rear humerus swing in a yaw/roll-driven world sagittal frame; forward range 45/62 degrees. Chest forward pitch is not added again to rear arm swing.',
            'authored_summary': {**summary, 'feet': {s: {k:v for k,v in foot.items() if k != 'joint_samples'} for s,foot in summary['feet'].items()}},
            'authored_joint_summary': {s:{k:v for k,v in row.items() if k != 'requested_source_joint_samples'} for s,row in joints.items()},
            'runtime_tested': False, 'rendered': False}
        manifest['clips'][role], actions[role] = entry, action
        print('M07_V18_BODY_GAIT_EXPORTED '+role+' '+json.dumps({'duration': duration,
            'stride_cm': entry['stride_cm'], 'max_settling_cm': max(settling),
            'body': entry['authored_summary'], 'joint_hinge': entry['authored_joint_summary']}), flush=True)
    for name, hidden in visibility.items():
        bpy.data.objects[name].hide_viewport = hidden
    motion.activate(rig, actions['Chase'])
    scene.frame_start, scene.frame_end = 1, manifest['clips']['Chase']['frames']
    scene.frame_set(0)
    rig['locomotion_revision'] = 'V18 single support-led whole-body rhythm, ankle-centered support, fixed lateral stance, original V17 shared knee hinge, forward spacious arm arcs'
    bpy.ops.wm.save_as_mainfile(filepath=manifest['source'], compress=True)
    manifest.update(source_saved=True, animation_fbx_exported=True,
        donor_provenance='Cycle/rhythm lineage: original installed Epic Walk/Jog adaptation from RunningV12; V18 authored locally on unchanged Meshy-derived original rig, using source support diagnosis rather than claiming direct unedited motion capture.')
    write(OUT/'body_gait_manifest_v18.json', manifest)
    print('M07_V18_BODY_GAIT_SAVED '+manifest['source'], flush=True)


if __name__ == '__main__':
    main()
