"""Replace only M07 V22 clavicle/arm/hand curves with inward swinging claws.

The user accepted the legs/feet and asked for medial palms plus arm swing
locked to the existing step cadence. Copy the V22 Actions, retaining every
non-arm FCurve, contact interval, pelvis curve and playback speed verbatim.
No runtime test, render, screenshot or interactive editor launch.
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
OUT = ROOT/'InwardArmSwingV23/Motion'
SOURCE_MANIFEST = ROOT/'HeavyGaitV22/Motion/heavy_gait_manifest_v22.json'
SOURCE = ROOT/'HeavyGaitV22/Motion/M07_Original_HeavyGait_V22.blend'
sys.path.insert(0, str(Path(__file__).parent))
import author_heavy_gait_v22 as v22
import author_motion_v04 as motion
import author_running_v12 as running
import author_locomotion_death_v15 as v15
import author_leg_joint_motion_v17 as v17
import author_palm_arm_motion_v20 as v20
from author_cast_v15 import signed_angle

FPS = 30
UP, RIGHT, FORWARD = v22.UP, v22.RIGHT, v22.FORWARD
PREFIXES = ('clavicle_',) + v20.ARM_PREFIXES
SWING = [(0., -18.), (.10, -24.), (.25, -7.), (.43, 23.),
         (.50, 29.), (.62, 24.), (.78, 6.), (.93, -10.)]
ELBOW = [(0., 20.), (.15, 18.), (.30, 26.), (.50, 36.),
         (.65, 33.), (.80, 26.), (.94, 21.)]
CONFIG = {
    'SlowWalk': dict(swing_gain=.94, shoulder_lag_s=.025, upperarm_lag_s=.045,
                    elbow_lag_s=.075, wrist_lag_s=.11, abduction_deg=7.),
    'Chase': dict(swing_gain=1.06, shoulder_lag_s=.02, upperarm_lag_s=.035,
                 elbow_lag_s=.06, wrist_lag_s=.09, abduction_deg=8.),
}


def arm_reference(rest, side):
    reference = v20.arm_reference(rest, side)
    # The generated rest elbow is almost straight and bends backward/down.
    # Its unsigned cross product picked opposite anatomical branches on the
    # two arms. Orient the reference hinge by anterior elbow flexion in the
    # T-pose, retaining a signed rest bend (as for the existing knee solver).
    # This changes the solver basis, not any bone's edit/reference matrix.
    hinge = reference['hinge'].copy()
    anterior_hinge = reference['upper'].cross(FORWARD).normalized()
    if hinge.dot(anterior_hinge) < 0.:
        hinge.negate()
    reference['hinge'] = hinge
    reference['rest_bend'] = math.atan2(
        hinge.dot(reference['upper'].cross(reference['lower'])),
        reference['upper'].dot(reference['lower']))
    reference['reference_frame'] = motion.anatomical_frame(reference['upper'], hinge)
    return reference


def fingers(target, rest, local, ordered, side, reference, phase, duration):
    hand = 'hand_'+side
    delta = target[hand].to_quaternion()@rest[hand].to_quaternion().inverted()
    palm = delta@reference['palm_normal']
    # Mild phase-linked closing/opening follows the wrist, not a separate
    # finger-waving loop. Every digit retains its own anatomical chain.
    carry = v22.cyclic(ELBOW, phase-.12/duration)
    curl_gain = 1.+.12*(carry-27.)/9.
    for pose in ordered:
        name = pose.name
        if not name.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')) or not name.endswith('_'+side):
            continue
        parent = pose.parent.name
        position = target[parent]@local[name].translation
        q = target[parent].to_quaternion()@local[name].to_quaternion()
        if '_metacarpal_' not in name:
            digit, segment, _ = name.split('_')
            amount = (5., 9., 7.)[int(segment)-1]*curl_gain
            amount *= .56 if digit == 'thumb' else .92 if digit == 'pinky' else 1.
            direction = q@Vector((0., 1., 0.))
            axis = direction.cross(palm).normalized()
            q = v22.rot(axis, amount)@q
        target[name] = v22.matrix(position, q)


def arms(source, rest, local, ordered, references, phase, duration, config):
    target = {name: transform.copy() for name, transform in source.items()}
    chest = source['spine_05'].to_quaternion()@rest['spine_05'].to_quaternion().inverted()
    records = {}
    for side, sign, offset in (('l', 1., 0.), ('r', -1., .5)):
        reference = references[side]
        own_phase = phase+offset
        shoulder_phase = own_phase-config['shoulder_lag_s']/duration
        upper_phase = own_phase-config['upperarm_lag_s']/duration
        elbow_phase = own_phase-config['elbow_lag_s']/duration
        wrist_phase = own_phase-config['wrist_lag_s']/duration
        swing = v22.cyclic(SWING, upper_phase)*config['swing_gain']
        bend = v22.cyclic(ELBOW, elbow_phase)
        clavicle = 'clavicle_'+side
        parent = next(p for p in ordered if p.name == clavicle).parent.name
        shoulder_lead = v22.cyclic(SWING, shoulder_phase)*.10
        clavicle_delta = chest@v22.rot(UP, -sign*shoulder_lead)
        target[clavicle] = v22.matrix(target[parent]@local[clavicle].translation,
            clavicle_delta@rest[clavicle].to_quaternion())
        shoulder = target[clavicle]@local['upperarm_'+side].translation

        # Left foot ahead -> left arm behind, right arm ahead; opposite at .5.
        # The upper arm is the driver. Elbow and wrist have small bounded
        # delays instead of holding a permanently forward-carried claw.
        sagittal = Vector((0., -math.sin(math.radians(swing)), -math.cos(math.radians(swing))))
        spread = math.radians(config['abduction_deg'])
        upper = (clavicle_delta@(sagittal*math.cos(spread)+RIGHT*(sign*math.sin(spread)))).normalized()
        front = clavicle_delta@FORWARD
        elbow_direction = (front-upper*front.dot(upper)).normalized()
        lower = (upper*math.cos(math.radians(bend))+elbow_direction*math.sin(math.radians(bend))).normalized()
        hinge = upper.cross(lower).normalized()
        du = (motion.anatomical_frame(upper, hinge)@reference['reference_frame'].transposed()).to_quaternion()
        dl = du@Quaternion(reference['hinge'], math.radians(bend)-reference['rest_bend'])

        # Medial is explicitly mirrored, in the current chest frame. The old
        # posterior target was not an inward-facing palm. Calibrating the
        # upper-arm hinge first avoids asking one wrist for a 180-degree flip.
        desired = chest@(-sign*RIGHT)
        projected = (desired-lower*desired.dot(lower)).normalized()
        normal = dl@reference['palm_normal']
        required_roll = math.degrees(signed_angle(normal, projected, lower))
        forearm_roll = v22.clamp(required_roll, -85., 85.)
        wrist_roll = v22.clamp(required_roll-forearm_roll, -6., 6.)
        forearm_delta = v22.rot(lower, forearm_roll)@dl
        hand_delta = v22.rot(lower, wrist_roll)@forearm_delta
        palm, along = hand_delta@reference['palm_normal'], hand_delta@reference['finger_along']
        across = palm.cross(along).normalized()
        wrist_yield = -2.+3.5*v22.cyclic(SWING, wrist_phase)/29.
        hand_delta = v22.rot(across, wrist_yield)@hand_delta
        elbow = shoulder+upper*reference['upper_length']
        wrist = elbow+lower*reference['lower_length']
        target['upperarm_'+side] = v22.matrix(shoulder, du@rest['upperarm_'+side].to_quaternion())
        target['lowerarm_'+side] = v22.matrix(elbow, forearm_delta@rest['lowerarm_'+side].to_quaternion())
        target['hand_'+side] = v22.matrix(wrist, hand_delta@rest['hand_'+side].to_quaternion())
        fingers(target, rest, local, ordered, side, reference, own_phase, duration)
        records[side] = dict(shoulder_lead_deg=shoulder_lead, upperarm_swing_deg=swing,
            elbow_flexion_deg=bend, requested_forearm_roll_deg=required_roll,
            forearm_roll_deg=forearm_roll, wrist_roll_deg=wrist_roll, wrist_yield_deg=wrist_yield,
            medial_direction=list(desired), authored_palm_normal=list(hand_delta@reference['palm_normal']),
            shoulder_cm=list(shoulder), elbow_cm=list(elbow), wrist_cm=list(wrist))
    return target, records


def insert_owned_frame(rig, target, rest, ordered, frame, previous):
    for pose in ordered:
        name = pose.name
        if not name.startswith(PREFIXES):
            continue
        parent = pose.parent.name
        pose.matrix_basis = pose.bone.convert_local_to_pose(target[name], rest[name],
            parent_matrix=target[parent], parent_matrix_local=rest[parent], invert=True)
        pose.rotation_mode = 'QUATERNION'
        pose.location = Vector()
        pose.scale = Vector((1., 1., 1.))
        q = pose.rotation_quaternion.copy()
        if name in previous and previous[name].dot(q) < 0.:
            q.negate()
        pose.rotation_quaternion = q
        previous[name] = q.copy()
        for channel in ('location', 'rotation_quaternion', 'scale'):
            pose.keyframe_insert(data_path=channel, frame=frame, group=name)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    old_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding='utf-8-sig'))
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    rig = v20.original_rig()
    rig.data.pose_position = 'POSE'
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    rest = {bone.name: bone.matrix_local.copy() for bone in rig.data.bones}
    local = {bone.name: bone.parent.matrix_local.inverted()@bone.matrix_local if bone.parent else bone.matrix_local.copy()
             for bone in rig.data.bones}
    references = {side: arm_reference(rest, side) for side in ('l', 'r')}
    hidden = {obj.name: obj.hide_viewport for obj in bpy.data.objects if obj.type == 'MESH'}
    for name in hidden:
        bpy.data.objects[name].hide_viewport = True
    originals = {role: bpy.data.actions[old_manifest['clips'][role]['action']] for role in CONFIG}
    cache = {role: v17.cache_action(rig, action, old_manifest['clips'][role]['frames'], ordered)
             for role, action in originals.items()}
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.
    manifest = copy.deepcopy(old_manifest)
    manifest.update(revision='InwardArmSwingV23', source=str(OUT/'M07_Original_InwardArmSwing_V23.blend'),
        source_action_blend=str(SOURCE), source_action_manifest=str(SOURCE_MANIFEST),
        changed_bone_prefixes=list(PREFIXES), clips={},
        retained_channels='All non-clavicle/non-arm FCurves copied from V22 without re-keying; legs, feet, pelvis, spine, head, gills, duration and speed retained',
        user_feedback='V22 legs and feet largely satisfactory; arms stiff and palms facing outward',
        palm_target='Chest-local medial: left -X and right +X, mirrored actual finger-defined palm normals',
        elbow_basis='Signed rest flexion and anterior reference hinge; no bind-pose or skin edits',
        scope='Only two movement clips: clavicles, upper arms, forearms, wrists and fingers',
        choreography='Contralateral arm swing on unchanged V22 cadence; scapular lead, yielding elbows and wrists; medial palms',
        source_saved=False, animation_fbx_exported=False, ue_imported=False, ue_saved=False,
        tested=False, runtime_tested=False, rendered=False, visual_accepted=False, user_review_pending=True)
    manifest.pop('ue_save_receipt', None)
    actions = {}
    for role, config in CONFIG.items():
        entry = copy.deepcopy(old_manifest['clips'][role])
        count, duration = entry['frames'], entry['duration_seconds']
        action = originals[role].copy()
        action.name = 'A_M07_'+role+'_InwardArmSwingV23'
        action.use_fake_user = True
        motion.activate(rig, action)
        previous, production, first = {}, [], None
        for index, source in enumerate(cache[role]):
            frame, phase = index+1, index/(count-1)
            scene.frame_set(frame)
            target, record = arms(source, rest, local, ordered, references, phase, duration, config)
            if index == 0:
                first = {name: transform.copy() for name, transform in target.items() if name.startswith(PREFIXES)}
            elif index == count-1:
                target.update({name: transform.copy() for name, transform in first.items()})
            insert_owned_frame(rig, target, rest, ordered, frame, previous)
            production.append(dict(frame=frame, seconds=index/FPS, phase=phase, arms=record))
        for curve in running.curves(action):
            if any(('"'+prefix) in curve.data_path for prefix in PREFIXES):
                for key in curve.keyframe_points:
                    key.interpolation = 'LINEAR'
        fbx = OUT/('A_M07_'+role+'.fbx')
        v15.export(rig, action, fbx, count)
        record_path = OUT/('authored_'+role.lower()+'_arm_record_v23.json')
        v22.write(record_path, dict(scope='Intrinsic authoring data only; no pose/render test',
            rest_signed_elbow_deg={side: math.degrees(ref['rest_bend']) for side, ref in references.items()},
            frames=production, runtime_tested=False, rendered=False))
        entry.update(action=action.name, file=str(fbx),
            asset='/Game/Monsters/BlindSupplicantM07/AnimationsInwardArmV23/A_M07_'+role,
            source_action=originals[role].name, arm_config=config, production_record=str(record_path),
            nonarm_fcurves_copied=True)
        manifest['clips'][role], actions[role] = entry, action
        print('M07_V23_ARMS_EXPORTED '+role+' '+str(fbx), flush=True)
    for name, was_hidden in hidden.items():
        bpy.data.objects[name].hide_viewport = was_hidden
    motion.activate(rig, actions['SlowWalk'])
    scene.frame_start, scene.frame_end = 1, manifest['clips']['SlowWalk']['frames']
    scene.frame_set(1)
    rig['locomotion_revision'] = 'V23 inward palms and contralateral arm swing; V22 legs/body retained'
    bpy.ops.wm.save_as_mainfile(filepath=manifest['source'], compress=True)
    manifest.update(source_saved=True, animation_fbx_exported=True)
    v22.write(OUT/'inward_arm_swing_manifest_v23.json', manifest)
    print('M07_V23_ARMS_SOURCE_SAVED '+str(OUT), flush=True)


if __name__ == '__main__':
    main()
