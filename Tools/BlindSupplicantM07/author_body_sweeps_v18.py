"""M07 V18: one attacking arm, supported forward commitment and body-driven sweep.

The actual HundredEyed/Rampage shoulder-elbow-wrist sweep and temporal crossing
remain the motion source. V17 original geometry, skin and the immutable V11
83-bone reference are retained. The other arm keeps its hanging-idle local pose.
This producer saves source/FBX only; it does not launch UE, tests or renders.
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'BodyMotionV18/Attack'
MASTER = ROOT/'LegJointsV17/Skin/M07_Original_LegJoints_V17.blend'
FPS = 30
UP, RIGHT, FWD = Vector((0., 0., 1.)), Vector((1., 0., 0.)), Vector((0., -1., 0.))
sys.path.insert(0, str(Path(__file__).parent))
import author_motion_v04 as motion
import author_power_sweep_v16 as v16
from author_sweep_cast_v14 import export, read_donor
from author_cast_v15 import base_pose, solve_segments
from repair_attack_arms_v13 import curves, track


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def body_choreography(seconds, contact, duration, side, donor):
    p = v16.choreography(seconds, contact, duration, side, donor)
    # Explicit load -> release -> forward follow-through. The pelvis begins
    # advancing before the chest reaches its strike lean; its travel remains
    # inside the planted feet, rather than moving the Actor/root into a target.
    p['pelvis_shift'].y = track(seconds, [
        (0., 0.), (contact-.25, 2.), (contact-.13, 1.3),
        (contact-.035, -6.1), (contact+.09, -8.),
        (contact+.21, -7.1), (duration-.10, -.5), (duration, 0.)])
    p['pelvis_shift'].z = track(seconds, [
        (0., 0.), (contact-.24, -3.8), (contact-.12, -4.4),
        (contact+.045, -2.8), (contact+.17, -3.2), (duration, 0.)])
    p['pelvis_pitch_deg'] = track(seconds, [
        (0., 0.), (contact-.23, -1.), (contact-.12, -.3),
        (contact-.035, 3.1), (contact+.11, 4.), (duration, 0.)])
    p['body_lean_deg'] = track(seconds, [
        (0., 0.), (contact-.24, -2.2), (contact-.13, -1.2),
        (contact+.025, 11.2), (contact+.11, 12.5),
        (contact+.23, 9.), (duration-.10, 1.5), (duration, 0.)])
    p['body_roll_deg'] = track(seconds, [
        (0., 0.), (contact-.21, -1.2*p['mirror']),
        (contact+.035, 2.1*p['mirror']),
        (contact+.16, 1.4*p['mirror']), (duration, 0.)])
    p['support'] = 0.
    return p


def support_reference(baseline, side):
    hip, knee, ankle = (baseline[n+'_'+side].translation.copy()
                        for n in ('thigh', 'calf', 'foot'))
    u, l = (knee-hip).normalized(), (ankle-knee).normalized()
    hinge = u.cross(l).normalized()
    if hinge.dot(RIGHT) < 0.:
        hinge.negate()
    chord = (ankle-hip).normalized()
    pole = knee-hip-chord*(knee-hip).dot(chord)
    return {'hip': hip, 'knee': knee, 'ankle': ankle,
            'u': u, 'l': l, 'hinge': hinge, 'pole': pole.normalized(),
            'l1': (knee-hip).length, 'l2': (ankle-knee).length,
            'flex': math.atan2(hinge.dot(u.cross(l)), u.dot(l)),
            'frame': motion.anatomical_frame(u, hinge)}


def solve_support_leg(side, target, baseline, data):
    """One anatomical signed knee hinge, planted ankle and unchanged bone lengths.

    The actual hanging-idle knee plane is transported, so attack entrances and
    exits use the exact idle articulation. Independently solved calf roll was
    the old V16 defect; the calf now inherits the femur's single hinge frame.
    """
    d = data[side]
    hip = target['thigh_'+side].translation
    ankle = d['ankle']
    axis = (ankle-hip).normalized()
    distance = (ankle-hip).length
    maximum = math.sqrt(d['l1']**2+d['l2']**2
                        +2.*d['l1']*d['l2']*math.cos(math.radians(7.)))
    minimum = math.sqrt(d['l1']**2+d['l2']**2
                        +2.*d['l1']*d['l2']*math.cos(math.radians(140.)))
    distance = min(maximum, max(minimum, distance))
    ankle = hip+axis*distance
    pelvis_delta = target['pelvis'].to_quaternion()@baseline['pelvis'].to_quaternion().inverted()
    front = pelvis_delta@FWD
    yaw = math.atan2(front.x, -front.y)
    yaw = v16.clamp(yaw, math.radians(-10.), math.radians(10.))
    pole = Quaternion(UP, yaw)@d['pole']
    pole -= axis*pole.dot(axis)
    pole.normalize()
    along = (d['l1']**2-d['l2']**2+distance**2)/(2.*distance)
    height = math.sqrt(max(0., d['l1']**2-along**2))
    knee = hip+axis*along+pole*height
    u, l = (knee-hip).normalized(), (ankle-knee).normalized()
    hinge = u.cross(l).normalized()
    if hinge.dot(RIGHT) < 0.:
        hinge.negate()
    flex = math.atan2(hinge.dot(u.cross(l)), u.dot(l))
    upper_delta = (motion.anatomical_frame(u, hinge)@d['frame'].transposed()).to_quaternion()
    lower_delta = upper_delta@Quaternion(d['hinge'], flex-d['flex'])
    return {
        'thigh_'+side: Matrix.LocRotScale(hip, upper_delta@baseline['thigh_'+side].to_quaternion(), Vector((1.,1.,1.))),
        'calf_'+side: Matrix.LocRotScale(knee, lower_delta@baseline['calf_'+side].to_quaternion(), Vector((1.,1.,1.))),
        'foot_'+side: Matrix.LocRotScale(ankle, baseline['foot_'+side].to_quaternion(), Vector((1.,1.,1.)))
    }, math.degrees(flex)


def author_action(rig, rest, baseline, baseline_local, ordered, role, frames, contact, donor):
    action = bpy.data.actions.new('A_M07_'+role+'_BodySweepV18')
    action.use_fake_user = True
    motion.activate(rig, action)
    for p in ordered:
        p.rotation_mode = 'QUATERNION'
        p.matrix_basis = Matrix.Identity(4)
        for channel in ('location', 'rotation_quaternion', 'scale'):
            p.keyframe_insert(data_path=channel, frame=0)
    duration = (frames-1)/FPS
    attacking = 'l' if role == 'SweepLeft' else 'r'
    quiet = 'r' if attacking == 'l' else 'l'
    leg_data = {side: support_reference(baseline, side) for side in ('l', 'r')}
    previous, samples = {}, []
    lean_shares = {'spine_01': .12, 'spine_02': .18, 'spine_03': .23,
                   'spine_04': .25, 'spine_05': .22}
    for index in range(frames):
        frame, seconds = index+1, index/FPS
        bpy.context.scene.frame_set(frame)
        params = body_choreography(seconds, contact, duration, attacking, donor)
        target, forearm_goal, arm_q, support = {}, {}, {}, {}
        row = {'frame': frame, 'seconds': seconds, 'stage': params['stage'],
               'donor_seconds': params['donor_seconds'], 'body_yaw_deg': params['body_yaw_deg'],
               'pelvis_yaw_deg': params['pelvis_yaw_deg'],
               'pelvis_pitch_deg': params['pelvis_pitch_deg'],
               'additional_spine_forward_lean_deg': params['body_lean_deg'],
               'pelvis_shift_cm': list(params['pelvis_shift']),
               'quiet_arm_side': quiet, 'quiet_arm_local_pose': 'Exact original hanging idle',
               'arms': {}, 'support_feet': {}, 'knees': {}}
        for p in ordered:
            name, parent = p.name, p.parent.name if p.parent else None
            target[name] = p.bone.convert_local_to_pose(baseline_local[name], rest[name],
                **({'parent_matrix': target[parent], 'parent_matrix_local': rest[parent]} if parent else {}))
            if name == 'pelvis':
                q = (Quaternion(UP, math.radians(params['pelvis_yaw_deg']))
                     @Quaternion(RIGHT, math.radians(params['pelvis_pitch_deg']))
                     @baseline[name].to_quaternion())
                target[name] = Matrix.LocRotScale(baseline[name].translation+params['pelvis_shift'], q, Vector((1.,1.,1.)))
            elif name in lean_shares:
                fraction = lean_shares[name]
                extra_yaw = (params['body_yaw_deg']-params['pelvis_yaw_deg'])*fraction
                q = (Quaternion(UP, math.radians(extra_yaw))
                     @Quaternion(RIGHT, math.radians(params['body_lean_deg']*fraction))
                     @Quaternion(FWD, math.radians(params['body_roll_deg']*fraction))
                     @target[name].to_quaternion())
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1.,1.,1.)))
            elif name in ('neck_01', 'neck_02'):
                q = (Quaternion(UP, math.radians(-params['body_yaw_deg']*.17))
                     @Quaternion(RIGHT, math.radians(-params['body_lean_deg']*.09))
                     @target[name].to_quaternion())
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1.,1.,1.)))
            elif name == 'clavicle_'+attacking:
                sign = 1. if attacking == 'l' else -1.
                q = Quaternion(UP, math.radians(-sign*params['clavicle_protraction_deg']))@target[name].to_quaternion()
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1.,1.,1.)))
            torso = (target['spine_05'].to_quaternion()@baseline['spine_05'].to_quaternion().inverted()
                     if 'spine_05' in target else Quaternion())
            # The quiet shoulder/upper arm/elbow/wrist/fingers are deliberately
            # left at the inherited baseline-local matrices above. Only the
            # torso carries them; there is no copied balance or mirrored sweep.
            if name == 'upperarm_'+attacking:
                goal, pole, a, b = v16.wrist_goal(attacking, attacking, target[name].translation,
                    target['spine_05'].translation, torso, baseline, params)
                ceiling = .9999-(.9999-.968)*params['active']
                u, l, reached = solve_segments(goal-target[name].translation, a, b, pole, ceiling)
                original = (baseline['lowerarm_'+attacking].translation-baseline[name].translation).normalized()
                q = (torso@original).rotation_difference(u)@torso@baseline[name].to_quaternion()
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1.,1.,1.)))
                forearm_goal[attacking], arm_q[attacking] = l, q
                row['arms'][attacking] = {'requested_wrist_cm': list(goal),
                    'elbow_bend_deg': math.degrees(u.angle(l)),
                    'reach_fraction': reached.length/(a+b), 'extra_axial_upper_roll_deg': 0.}
            elif name == 'lowerarm_'+attacking:
                original = (baseline['hand_'+attacking].translation-baseline[name].translation).normalized()
                upper_delta = arm_q[attacking]@baseline['upperarm_'+attacking].to_quaternion().inverted()
                q = (upper_delta@original).rotation_difference(forearm_goal[attacking])@upper_delta@baseline[name].to_quaternion()
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1.,1.,1.)))
            elif name == 'hand_'+attacking:
                lower = 'lowerarm_'+attacking
                lower_delta = target[lower].to_quaternion()@baseline[lower].to_quaternion().inverted()
                q = lower_delta@baseline[name].to_quaternion()
                q = Quaternion(q@RIGHT, math.radians(params['wrist_flex_deg']))@q
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1.,1.,1.)))
            elif name.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')) and name.endswith('_'+attacking) and '_metacarpal_' not in name:
                digit, segment = name.split('_')[0], int(name.split('_')[1])-1
                hand = 'hand_'+attacking
                hand_delta = target[hand].to_quaternion()@rest[hand].to_quaternion().inverted()
                along = (rest['middle_01_'+attacking].translation-rest[hand].translation).normalized()
                across = (rest['index_01_'+attacking].translation-rest['pinky_01_'+attacking].translation).normalized()
                normal = hand_delta@along.cross(across).normalized()
                direction = target[name].to_3x3()@Vector((0.,1.,0.))
                axis = direction.cross(normal).normalized()
                delay = {'thumb': 0., 'index': .015, 'middle': .025, 'ring': .04, 'pinky': .05}[digit]+segment*.012
                amount = v16.clamp((params['claw']-delay)/(1.-delay))
                flex = (10.,16.,12.)[segment] if digit != 'thumb' else (5.,9.,7.)[segment]
                q = Quaternion(axis, math.radians(flex*amount))@target[name].to_quaternion()
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1.,1.,1.)))
            elif name.startswith('thigh_'):
                side = name[-1]
                support[side], flex = solve_support_leg(side, target, baseline, leg_data)
                target[name] = support[side][name]
                row['knees'][side] = {'signed_flexion_deg': flex, 'common_anatomical_hinge': True}
            elif name.startswith(('calf_', 'foot_')):
                target[name] = support[name[-1]][name]
            p.matrix_basis = p.bone.convert_local_to_pose(target[name], rest[name],
                **({'parent_matrix': target[parent], 'parent_matrix_local': rest[parent]} if parent else {}), invert=True)
            p.rotation_mode = 'QUATERNION'
            q = p.rotation_quaternion.copy()
            if name in previous and q.dot(previous[name]) < 0.:
                q.negate()
            p.rotation_quaternion = q
            previous[name] = q.copy()
            p.scale = Vector((1.,1.,1.))
            if name != 'pelvis':
                p.location = Vector()
            for channel in ('location', 'rotation_quaternion', 'scale'):
                p.keyframe_insert(data_path=channel, frame=frame)
        for side in ('l', 'r'):
            row['arms'].setdefault(side, {})
            row['arms'][side].update({part+'_cm': list(target[part+'_'+side].translation)
                for part in ('upperarm', 'lowerarm', 'hand')})
            row['support_feet'][side] = list(target['foot_'+side].translation)
        row['chest_cm'] = list(target['spine_05'].translation)
        row['head_cm'] = list(target['head'].translation)
        samples.append(row)
    for curve in curves(action):
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
    return action, samples


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.data.bones.get('gill_01_00'))
    original = json.loads((ROOT/'RecoveryOriginalV13/motion_manifest_v13.json').read_text(encoding='utf-8'))
    idle_name = original['clips']['Idle']['action']
    if idle_name not in bpy.data.actions:
        with bpy.data.libraries.load(str(ROOT/'RecoveryOriginalV13/M07_Original_Recovery_V13.blend'), link=False) as (available, loaded):
            loaded.actions = [idle_name]
    hidden = {o.name: o.hide_viewport for o in bpy.data.objects if o.type == 'MESH'}
    for name in hidden:
        bpy.data.objects[name].hide_viewport = True
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    baseline, baseline_local = base_pose(rig, original)
    donor = read_donor('Attack_Biped_Melee_A')
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.
    scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', .01
    rig.data.pose_position = 'POSE'
    entries, samples, actions = {}, {}, {}
    for role, frames, contact in (('SweepLeft', 34, .47), ('SweepRight', 37, .50)):
        action, authored = author_action(rig, rest, baseline, baseline_local, ordered, role, frames, contact, donor)
        file = OUT/('A_M07_'+role+'.fbx')
        export(rig, action, file, frames)
        duration = (frames-1)/FPS
        entries[role] = {'file': str(file), 'action': action.name, 'frames': frames, 'fps': FPS,
            'duration': duration, 'seconds': duration,
            'asset': '/Game/Monsters/BlindSupplicantM07/AnimationsBodyMotionV18/A_M07_'+role,
            'contact_time': contact, 'contact_seconds': contact, 'impact_seconds': contact,
            'contact_window_seconds': .12, 'contact_window_start_seconds': contact-.06,
            'contact_window_end_seconds': contact+.06, 'loop': False, 'root_motion': False,
            'runtime_melee_playback_multiplier': 1.30,
            'expected_runtime_duration_seconds': duration/1.30,
            'expected_runtime_contact_seconds': contact/1.30,
            'reference_only_blender_frame': 0, 'exported_blender_frame_start': 1,
            'exported_blender_frame_end': frames, 'bone_tracks': list(rest),
            'source_time_map': v16.sweep_time_map(contact, duration),
            'quiet_arm_side': 'r' if role == 'SweepLeft' else 'l',
            'quiet_arm_local_pose': 'Exact original drooped idle in shoulder/elbow/wrist/fingers; torso following only'}
        samples[role], actions[role] = authored, action
        print('M07_V18_BODY_SWEEP_EXPORTED '+role+' '+str(file), flush=True)
    for name, value in hidden.items():
        bpy.data.objects[name].hide_viewport = value
    motion.activate(rig, actions['SweepRight'])
    scene.frame_start, scene.frame_end = 1, entries['SweepRight']['frames']
    scene.frame_set(0)
    source = OUT/'M07_Original_BodySweeps_V18.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True)
    write(OUT/'body_sweep_manifest_v18.json', {
        'revision': 'BodySweepV18', 'source': str(source), 'source_master': str(MASTER),
        'clips': entries, 'fps': FPS, 'reference_skeleton': '/Game/Monsters/BlindSupplicantM07/SK_M07_ReferenceOriginalV11',
        'bone_names': list(rest), 'reference_bones': {n: motion.rows(m) for n,m in rest.items()},
        'bone_parents': {b.name: b.parent.name if b.parent else None for b in rig.data.bones},
        'rig_object_matrix_world': motion.rows(rig.matrix_world),
        'reference_pose_modified': False, 'geometry_modified': False, 'weights_modified': False,
        'source_reference': {'monster': 'HundredEyedSlag', 'formal_role': 'AttackSweep_R',
            'formal_asset': '/Game/Monsters/HundredEyedSlag/V1/Animations/A_HundredEyedSlag_AttackSweep_R',
            'donor_asset': donor['asset'], 'donor_file': str(v16.DONOR/'Attack_Biped_Melee_A.json'),
            'source_author': str(PROJECT/'SourceAssets/HundredEyedSlagMeshy20260930/RampageV8/author_rampage.py'),
            'method': 'Actual upperarm/lowerarm/hand component positions and source pelvis/spine rotation. Preserve outward load, hip/chest/shoulder sequential lead, .30-.39s fast frontal source crossing and .39-.52s follow-through; add humanoid forward-supported weight transfer.'},
        'changes_from_v16': {'other_arm_active_counterbalance_removed': True,
            'other_arm_clavicle_protraction_removed': True, 'other_hand_extra_curl_removed': True,
            'pelvis_forward_peak_cm': 8., 'pelvis_forward_peak_after_contact_seconds': .09,
            'pelvis_pitch_peak_deg': 4., 'extra_spine_forward_peak_deg': 12.5,
            'upperbody_weight_transfer': 'Load back with lowered pelvis, pelvis advances before contact, sternum follows and leans forward through impact, then whole-body recovery over planted feet',
            'torso_yaw_source_gain': .46, 'torso_yaw_limit_deg': 49.,
            'arm_arc_source_gain': .90, 'duration_contact_window_and_1_30_playback_contract_preserved': True,
            'leg_change': 'Replace independent V16 calf swing with signed shared anatomical knee hinge and exact hanging-idle knee plane; planted ankle and fixed lengths'},
        'child_location_policy': 'Only original pelvis carries authored movement; every child location zero, every bone scale one, Blender frame0 reference omitted from export',
        'unrelated_skin_and_geometry': 'Retained complete original V17 mesh, V16 arms/V17 legs weights, all six gills, original UV and immutable 83 bone bind',
        'authoring_samples': samples, 'source_saved': True, 'animation_fbx_exported': True,
        'ue_imported': False, 'ue_saved': False, 'tested': False, 'runtime_tested': False,
        'rendered': False, 'visual_accepted': False, 'user_review_pending': True})
    print('M07_V18_BODY_SWEEP_SOURCE_SAVED '+str(source), flush=True)


if __name__ == '__main__':
    main()
