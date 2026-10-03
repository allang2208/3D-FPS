"""M07 V25: anterior gait arm corridor, baked tissue clearance, body-led sweeps.

Copies accepted movement body/leg curves; only clavicle/arm/digit and free
gill-joint curves change. Two new melee clips share the current idle pose.
Production/export only; no simulation, render or acceptance tests.
"""
import copy
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'ClearanceSweepV25/Motion'
SOURCE = ROOT/'InwardArmSwingV23/Motion/M07_Original_InwardArmSwing_V23.blend'
SOURCE_MANIFEST = ROOT/'InwardArmSwingV23/Motion/inward_arm_swing_manifest_v23.json'
IDLE_SOURCE = ROOT/'PalmArmMotionV20/Motion/M07_Original_PalmArmMotion_V20.blend'
sys.path.insert(0, str(Path(__file__).parent))
import author_motion_v04 as motion
import author_running_v12 as running
import author_locomotion_death_v15 as v15
import author_leg_joint_motion_v17 as v17
import author_body_sweeps_v18 as v18
import author_palm_arm_motion_v20 as v20
import author_heavy_gait_v22 as v22
import author_inward_arm_swing_v23 as v23
import m07_clearance_v25 as clearance
from author_cast_v15 import arc, solve_segments, pole_from_pose, signed_angle, limit_swing
from author_sweep_cast_v14 import palm_frame

FPS = 30
UP, RIGHT, FORWARD = v22.UP, v22.RIGHT, v22.FORWARD
ramp, rot, matrix = v22.ramp, v22.rot, v22.matrix
SWEEPS = {'SweepLeft': dict(side='l', duration=1.4, contact=.60),
          'SweepRight': dict(side='r', duration=1.5, contact=20./30.)}


def arm_chain(target, rest, local, baseline, base_local, ordered, reference, side,
              goal, pole, palm_goal, amount, curl):
    upper_name, lower_name, hand_name = ['%s_%s'%(p, side) for p in ('upperarm', 'lowerarm', 'hand')]
    shoulder = target['clavicle_'+side]@local[upper_name].translation
    upper, lower, _ = solve_segments(goal-shoulder, reference['upper_length'],
        reference['lower_length'], pole, .9999-.035*amount)
    hinge = upper.cross(lower).normalized()
    du = (motion.anatomical_frame(upper, hinge)@reference['reference_frame'].transposed()).to_quaternion()
    dl = du@Quaternion(reference['hinge'], upper.angle(lower)-reference['rest_bend'])
    upper_q = target[upper_name].to_quaternion().slerp(du@rest[upper_name].to_quaternion(), amount)
    target[upper_name] = matrix(shoulder, upper_q)
    lower_position = target[upper_name]@local[lower_name].translation
    base_lower = target[upper_name]@(baseline[upper_name].inverted()@baseline[lower_name])
    lower_q = base_lower.to_quaternion().slerp(dl@rest[lower_name].to_quaternion(), amount)
    lower_delta = lower_q@rest[lower_name].to_quaternion().inverted()
    direction = lower_delta@reference['lower']
    goal_delta = palm_goal@rest[hand_name].to_quaternion().inverted()
    roll = signed_angle(lower_delta@reference['palm_normal'], goal_delta@reference['palm_normal'], direction)
    roll = v22.clamp(roll, math.radians(-80.), math.radians(80.))*amount
    lower_q = Quaternion(direction, roll)@lower_q
    target[lower_name] = matrix(lower_position, lower_q)
    hand_position = target[lower_name]@local[hand_name].translation
    base_hand = target[lower_name]@(baseline[lower_name].inverted()@baseline[hand_name])
    residual = palm_goal@base_hand.to_quaternion().inverted()
    hand_q = base_hand.to_quaternion().slerp(limit_swing(residual, 35.)@base_hand.to_quaternion(), amount)
    target[hand_name] = matrix(hand_position, hand_q)
    normal = (hand_q@rest[hand_name].to_quaternion().inverted())@reference['palm_normal']
    for pose in ordered:
        name = pose.name
        if not name.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')) or not name.endswith('_'+side):
            continue
        parent = pose.parent.name
        inherited = target[parent]@(baseline[parent].inverted()@baseline[name])
        point, q = inherited.translation, inherited.to_quaternion()
        if '_metacarpal_' not in name:
            digit, segment, _ = name.split('_')
            flex = curl[int(segment)-1]*(.65 if digit == 'thumb' else 1.)
            raw_q = target[parent].to_quaternion()@local[name].to_quaternion()
            axis = (raw_q@Vector((0., 1., 0.))).cross(normal).normalized()
            q = q.slerp(rot(axis, flex)@raw_q, amount)
        target[name] = matrix(point, q)


def sweep_pose(rest, local, baseline, base_local, ordered, references, leg_data, spec, t):
    side = spec['side']
    sign = 1. if side == 'l' else -1.
    contact, duration = spec['contact'], spec['duration']
    windup_end, follow_end = contact-.20, contact+.16
    recovery = ramp(t, follow_end+.045, duration)
    active = ramp(t, .0, windup_end*.8)*(1.-recovery)
    coil = ramp(t, .025, windup_end-.035)*(1.-recovery)
    hip_turn = ramp(t, contact-.245, contact+.07)
    chest_turn = ramp(t, contact-.20, contact+.13)
    pelvis_yaw = sign*(8.*coil-19.*hip_turn*(1.-recovery))
    chest_yaw = sign*(19.*coil-43.*chest_turn*(1.-recovery))
    lean = (-2.*coil+12.*ramp(t, contact-.18, contact+.08)*(1.-recovery))
    shift = Vector((sign*(3.*coil-5.*hip_turn*(1.-recovery)),
                    2.*coil-10.*hip_turn*(1.-recovery), -3.7*coil+1.2*hip_turn*(1.-recovery)))
    target = {}
    leg_solutions = {}
    for pose in ordered:
        name = pose.name
        parent = pose.parent.name if pose.parent else None
        target[name] = pose.bone.convert_local_to_pose(base_local[name], rest[name],
            **({'parent_matrix': target[parent], 'parent_matrix_local': rest[parent]} if parent else {}))
        point, q = target[name].translation, target[name].to_quaternion()
        if name == 'pelvis':
            point = baseline[name].translation+shift
            q = rot(UP, pelvis_yaw)@baseline[name].to_quaternion()
        elif name.startswith('spine_'):
            q = rot(UP, (chest_yaw-pelvis_yaw)*.2)@rot(RIGHT, lean*.2)@q
        elif name.startswith('neck_'):
            q = rot(UP, -chest_yaw*.13)@rot(RIGHT, -lean*.10)@q
        elif name == 'clavicle_'+side:
            q = rot(UP, -sign*(-4.*coil+11.*chest_turn*(1.-recovery)))@q
        elif name.startswith('clavicle_'):
            q = rot(UP, sign*2.5*active)@q
        target[name] = matrix(point, q)
        if name.startswith('thigh_'):
            s = name[-1]
            leg_solutions[s], _ = v18.solve_support_leg(s, target, baseline, leg_data)
            target[name] = leg_solutions[s][name]
        elif name.startswith(('calf_', 'foot_')):
            target[name] = leg_solutions[name[-1]][name]
    delta = target['spine_05'].to_quaternion()@baseline['spine_05'].to_quaternion().inverted()
    chest = target['spine_05'].translation
    for s in ('l', 'r'):
        direction_sign = 1. if s == 'l' else -1.
        shoulder = target['upperarm_'+s].translation
        hanging = shoulder+delta@(baseline['hand_'+s].translation-baseline['upperarm_'+s].translation)
        if s == side:
            wound = Vector((sign*78., -28., -30.))
            impact = Vector((sign*10., -84., -44.))
            crossed = Vector((-sign*28., -58., -51.))
            tangent = Vector((-sign*400., 0., -60.))
            if t < windup_end:
                destination = chest+delta@wound
                goal = arc(hanging, hanging+delta@Vector((sign*18., -12., 18.)),
                    destination+delta@Vector((sign*7., 4., -14.)), destination, ramp(t, .035, windup_end))
            else:
                if t <= contact:
                    u = min(1., (t-windup_end)/(contact-windup_end))
                    point = arc(wound, wound, impact-tangent*((contact-windup_end)/3.), impact, u)
                else:
                    u = min(1., (t-contact)/(follow_end-contact))
                    point = arc(impact, impact+tangent*((follow_end-contact)/3.), crossed, crossed, u)
                crossed_world = chest+delta@point
                goal = arc(crossed_world, crossed_world+delta@Vector((-sign*4., -9., -8.)),
                    hanging+delta@Vector((sign*12., -20., 15.)), hanging, recovery)
            pole = delta@Vector((sign*.9, .12, -.8)).normalized().lerp(
                Vector((sign*.45, -.05, -1.)).normalized(), chest_turn*.65)
            along = Vector((0., -.35-.5*chest_turn, -1.+.3*chest_turn)).normalized()
            normal = Vector((-sign, -.12, -.15)).normalized()
            curl = (10., 19., 13.)
        else:
            # The other arm keeps a quiet medial-palm pose with a small forward
            # counterbalance. It never performs a second mirrored claw strike.
            goal = hanging+delta@Vector((-sign*4., -14., 5.))*active
            pole = delta@pole_from_pose(baseline['upperarm_'+s].translation,
                baseline['lowerarm_'+s].translation, baseline['hand_'+s].translation,
                Vector((direction_sign, 0., -1.)))
            along = Vector((0., -.22, -1.))
            normal = Vector((-direction_sign, 0., 0.))
            curl = (5., 9., 7.)
        palm = delta@palm_frame(along, normal)@palm_frame(references[s]['finger_along'],
            references[s]['palm_normal']).inverted()@rest['hand_'+s].to_quaternion()
        arm_chain(target, rest, local, baseline, base_local, ordered, references[s], s,
                  goal, pole, palm, active, curl)
    clearance.inherit_gills(target, baseline, ordered)
    return target


def key_owned(rig, target, rest, ordered, frame, previous):
    # Accepted body and legs retain their original Action FCurves verbatim.
    for pose in ordered:
        name = pose.name
        if not name.startswith(v23.PREFIXES) and not (name.startswith('gill_') and not name.endswith('_00')):
            continue
        parent = pose.parent.name
        pose.matrix_basis = pose.bone.convert_local_to_pose(target[name], rest[name],
            parent_matrix=target[parent], parent_matrix_local=rest[parent], invert=True)
        pose.rotation_mode = 'QUATERNION'
        pose.location, pose.scale = Vector(), Vector((1., 1., 1.))
        q = pose.rotation_quaternion.copy()
        if name in previous and q.dot(previous[name]) < 0.:
            q.negate()
        pose.rotation_quaternion = q
        previous[name] = q.copy()
        for channel in ('location', 'rotation_quaternion', 'scale'):
            pose.keyframe_insert(data_path=channel, frame=frame, group=name)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding='utf-8-sig'))
    profile = json.loads(clearance.PROFILE.read_text(encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    rig = v20.original_rig()
    rig.data.pose_position = 'POSE'
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    local = {b.name: b.parent.matrix_local.inverted()@b.matrix_local if b.parent else b.matrix_local.copy() for b in rig.data.bones}
    originals = {role: bpy.data.actions[source_manifest['clips'][role]['action']] for role in ('SlowWalk', 'Chase')}
    cache = {role: v17.cache_action(rig, action, source_manifest['clips'][role]['frames'], ordered) for role, action in originals.items()}
    with bpy.data.libraries.load(str(IDLE_SOURCE), link=False) as (_, loaded):
        loaded.actions = ['A_M07_Idle_PalmArmV20']
    baseline = v17.cache_action(rig, loaded.actions[0], 1, ordered)[0]
    base_local = {p.name: p.bone.convert_local_to_pose(baseline[p.name], rest[p.name],
        **({'parent_matrix': baseline[p.parent.name], 'parent_matrix_local': rest[p.parent.name]} if p.parent else {}), invert=True) for p in ordered}
    references = {s: v23.arm_reference(rest, s) for s in ('l', 'r')}
    leg_data = {s: v18.support_reference(baseline, s) for s in ('l', 'r')}
    hidden = {o.name: o.hide_viewport for o in bpy.data.objects if o.type == 'MESH'}
    for name in hidden:
        bpy.data.objects[name].hide_viewport = True
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.
    scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', .01
    # Keep the cadence and visible swing, but prevent the entire long forearm
    # and claw from travelling behind the torso into the membrane side folds.
    v23.SWING = [(0., 5.), (.10, 2.), (.25, 13.), (.43, 33.), (.50, 38.),
                 (.62, 32.), (.78, 19.), (.93, 8.)]
    v23.ELBOW = [(0., 34.), (.15, 32.), (.30, 38.), (.50, 46.),
                 (.65, 42.), (.80, 36.), (.94, 34.)]
    manifest = dict(revision='ClearanceSweepV25', source=str(OUT/'M07_Original_ClearanceSweep_V25.blend'),
        movement_source=str(SOURCE), idle_source=str(IDLE_SOURCE), surface_profile=str(clearance.PROFILE),
        fps=FPS, clips={}, reference_skeleton=source_manifest['reference_skeleton'],
        melee_playback_rate=1., contact_window_seconds=.14, gill_runtime_max_opening_degrees=18.,
        movement_policy='Original V23 non-arm/non-free-gill FCurves copied exactly; source/gameplay speeds retained',
        clearance_policy='Anterior arm corridor and original-surface FK opening baked offline; bounded native correction for blending',
        geometry_modified=False, weights_modified=False, reference_pose_modified=False,
        source_saved=False, animation_fbx_exported=False, ue_imported=False, ue_saved=False,
        runtime_tested=False, tested=False, rendered=False, user_review_pending=True)
    actions = {}
    for role in ('SlowWalk', 'Chase', 'SweepLeft', 'SweepRight'):
        walking = role in originals
        entry = copy.deepcopy(source_manifest['clips'][role]) if walking else dict(SWEEPS[role])
        duration = entry['duration_seconds'] if walking else entry['duration']
        count = entry['frames'] if walking else round(duration*FPS)+1
        action = originals[role].copy() if walking else bpy.data.actions.new('A_M07_'+role+'_ClearanceSweepV25')
        action.name = 'A_M07_'+role+'_ClearanceSweepV25'
        action.use_fake_user = True
        motion.activate(rig, action)
        previous, first = {}, None
        for index in range(count):
            scene.frame_set(index+1)
            if walking:
                config = dict(v23.CONFIG[role], abduction_deg=10., swing_gain=.94 if role == 'SlowWalk' else 1.)
                source = cache[role][index]
                target, _ = v23.arms(source, rest, local, ordered, references, index/(count-1), duration, config)
                clearance.inherit_gills(target, source, ordered)
            else:
                target = sweep_pose(rest, local, baseline, base_local, ordered, references, leg_data, SWEEPS[role], index/FPS)
                if index in (0, count-1):
                    target = {name: transform.copy() for name, transform in baseline.items()}
            clearance.bake_clearance(target, rest, profile)
            if index == 0:
                first = {name: transform.copy() for name, transform in target.items()}
            elif index == count-1:
                target = first
            if walking:
                key_owned(rig, target, rest, ordered, index+1, previous)
            else:
                running.insert_frame(rig, target, rest, ordered, index+1, previous)
        scene.frame_set(0)
        if not walking:
            for pose in ordered:
                pose.matrix_basis = Matrix.Identity(4)
                for channel in ('location', 'rotation_quaternion', 'scale'):
                    pose.keyframe_insert(data_path=channel, frame=0, group=pose.name)
        for curve in running.curves(action):
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        fbx = OUT/('A_M07_'+role+'.fbx')
        v15.export(rig, action, fbx, count)
        entry.update(role=role, action=action.name, file=str(fbx), fps=FPS, frames=count,
            duration_seconds=duration, loop=walking, root_motion=False,
            asset='/Game/Monsters/BlindSupplicantM07/AnimationsClearanceSweepV25/A_M07_'+role,
            source_action=originals[role].name if walking else 'Original V25 choreography from current V20 idle',
            nonarm_nongill_fcurves_copied=walking, baked_clearance=True,
            reference_only_blender_frame=0, exported_blender_frame_start=1, exported_blender_frame_end=count)
        if not walking:
            entry.update(contact_seconds=SWEEPS[role]['contact'], runtime_melee_playback_multiplier=1.)
        for stale in ('production_record', 'arm_config'):
            entry.pop(stale, None)
        manifest['clips'][role], actions[role] = entry, action
        print('M07_V25_CLIP_EXPORTED '+role+' '+str(fbx), flush=True)
    for name, value in hidden.items():
        bpy.data.objects[name].hide_viewport = value
    motion.activate(rig, actions['SlowWalk'])
    scene.frame_start, scene.frame_end = 1, manifest['clips']['SlowWalk']['frames']
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=manifest['source'], compress=True)
    manifest.update(source_saved=True, animation_fbx_exported=True)
    v22.write(OUT/'clearance_sweep_manifest_v25.json', manifest)
    print('M07_V25_SOURCE_SAVED '+str(OUT), flush=True)


if __name__ == '__main__':
    main()
