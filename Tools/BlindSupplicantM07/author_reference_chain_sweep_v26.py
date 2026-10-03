"""M07: retarget HundredEyed's original Rampage melee as one anatomical arm.

Production/export only. The current idle calibrates the shoulder/elbow chain;
the elbow has one hinge, no independent forearm roll or world-space palm aim.
The donor's body motion and timing drive two grounded, mirrored sweeps.
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'ReferenceChainSweepV26/Motion'
SOURCE = ROOT/'PalmArmMotionV20/Motion/M07_Original_PalmArmMotion_V20.blend'
sys.path.insert(0, str(Path(__file__).parent))
import author_motion_v04 as motion
import author_running_v12 as running
import author_locomotion_death_v15 as v15
import author_leg_joint_motion_v17 as v17
import author_body_sweeps_v18 as v18
import author_palm_arm_motion_v20 as v20
import m07_clearance_v25 as clearance
from author_sweep_cast_v14 import read_donor, sample_donor, palm_frame
from author_power_sweep_v16 import shaped_time, sweep_time_map
from author_cast_v15 import limit_swing, signed_angle

FPS = 30
UP, RIGHT, FWD = Vector((0., 0., 1.)), Vector((1., 0., 0.)), Vector((0., -1., 0.))
MIRROR = Matrix(((-1., 0., 0.), (0., 1., 0.), (0., 0., 1.)))
SPECS = {'SweepLeft': dict(side='l', duration=1.4, contact=.60),
         'SweepRight': dict(side='r', duration=1.5, contact=20./30.)}


def clamp(x, a, b):
    return max(a, min(b, x))


def smooth(t, a, b):
    x = clamp((t-a)/(b-a), 0., 1.)
    return x*x*x*(10.-15.*x+6.*x*x)


def matrix(p, q):
    return Matrix.LocRotScale(p, q, Vector((1., 1., 1.)))


def mirrored(q, side):
    return (MIRROR@q.to_matrix()@MIRROR).to_quaternion() if side == 'l' else q.copy()


def bounded(x, maximum):
    return maximum*math.tanh(x/maximum)


def reference(pose, side):
    s, e, w = [pose[n+'_'+side].translation for n in ('upperarm', 'lowerarm', 'hand')]
    u, l = (e-s).normalized(), (w-e).normalized()
    n = u.cross(l).normalized()
    return dict(u=u, l=l, n=n, bend=u.angle(l), upper_frame=palm_frame(u, n),
                lower_frame=palm_frame(l, n))


def source_chain(src, neutral, side):
    names = [n+'_'+side for n in ('upperarm', 'lowerarm', 'hand')]
    s, e, w = [src[n][0] for n in names]
    sb, eb, wb = [neutral[n][0] for n in names]
    u, l = (e-s).normalized(), (w-e).normalized()
    ub, lb = (eb-sb).normalized(), (wb-eb).normalized()
    nb = ub.cross(lb).normalized()
    transported = src[names[0]][1]@neutral[names[0]][1].inverted()@nb
    n = u.cross(l)
    if n.length < 1.e-5:
        n = transported.copy()
    else:
        n.normalize()
        if n.dot(transported) < 0.:
            n.negate()
        n = transported.lerp(n, smooth(u.angle(l), math.radians(3.), math.radians(12.))).normalized()
    bend = clamp(math.atan2(n.dot(u.cross(l)), u.dot(l)), math.radians(14.), math.radians(100.))
    return dict(u=u, l=l, n=n, bend=bend, upper_frame=palm_frame(u, n),
                lower_frame=palm_frame(l, n), upper0=palm_frame(ub, nb), lower0=palm_frame(lb, nb))


def body_tracks(donor, neutral):
    # Unwrap before attenuating the large donor turn. Crossing +/-180 degrees
    # must never flip M07's reduced chest/hip motion to the opposite side.
    tracks = {name: [] for name in ('pelvis', 'spine_03')}
    for name, rows in tracks.items():
        previous = 0.
        for src in donor['frames']:
            q = src[name][1]@neutral[name][1].inverted()
            forward, right = q@FWD, q@RIGHT
            yaw = math.atan2(forward.x, -forward.y)
            while yaw-previous > math.pi:
                yaw -= 2.*math.pi
            while yaw-previous < -math.pi:
                yaw += 2.*math.pi
            previous = yaw
            rows.append(Vector((yaw, -math.asin(clamp(forward.z, -1., 1.)),
                                -math.asin(clamp(right.z, -1., 1.)))))
    return tracks


def body_rotation(tracks, name, seconds, fps, side, weight, factor, limits):
    f = clamp(seconds*fps, 0., len(tracks[name])-1.)
    i = int(f)
    angles = tracks[name][i].lerp(tracks[name][min(i+1, len(tracks[name])-1)], f-i)
    angles = [bounded(v*k, math.radians(cap))*weight for v, k, cap in zip(angles, factor, limits)]
    q = Quaternion(UP, angles[0])@Quaternion(RIGHT, angles[1])@Quaternion(FWD, -angles[2])
    return mirrored(q, side)


def wrist_residual(chain, src, neutral, donor_side, amount):
    now = chain['lower_frame'].inverted()@src['hand_'+donor_side][1]
    base = chain['lower0'].inverted()@neutral['hand_'+donor_side][1]
    q = (now@base.inverted()).normalized()
    if q.w < 0.:
        q.negate()
    # The anatomical frame's X axis is the forearm axis. M07 lacks the donor's
    # twist bones, so keep this small correction at the wrist only.
    twist = Quaternion((q.w, q.x, 0., 0.))
    if twist.magnitude < 1.e-6:
        twist = Quaternion()
    else:
        twist.normalize()
    swing = q@twist.inverted()
    angle = bounded(2.*math.atan2(twist.x, twist.w), math.radians(8.))
    return Quaternion().slerp(limit_swing(swing, 18.)@Quaternion(RIGHT, angle), amount)


def pose_at(t, spec, donor, neutral, tracks, baseline, rest, ordered, refs, legs, locals_, state):
    keys = sweep_time_map(spec['contact'], spec['duration'])
    ds = shaped_time(t, keys)
    src = sample_donor(donor, ds)
    active = smooth(t, 0., spec['contact']-.25)*(1.-smooth(t, spec['duration']-.32, spec['duration']))
    hip_time = shaped_time(min(spec['duration'], t+.035), keys)
    chest_time = shaped_time(min(spec['duration'], t+.016), keys)
    hip_q = body_rotation(tracks, 'pelvis', hip_time, donor['fps'], spec['side'], active,
                          (.25, .12, .10), (15., 3., 2.))
    chest_q = body_rotation(tracks, 'spine_03', chest_time, donor['fps'], spec['side'], active,
                            (.40, .20, .14), (32., 9., 3.))
    hip_src = sample_donor(donor, hip_time)
    movement = (hip_src['pelvis'][0]-neutral['pelvis'][0])*.26
    movement = Vector((bounded(movement.x, 3.5), bounded(movement.y, 6.),
                       clamp(movement.z, -4., 1.5)-2.*active))*active
    if spec['side'] == 'l':
        movement = MIRROR@movement
    target, support = {}, {}
    for p in ordered:
        name = p.name
        target[name] = target[p.parent.name]@locals_[name] if p.parent else baseline[name].copy()
        point, q = target[name].translation, target[name].to_quaternion()
        if name == 'pelvis':
            point = baseline[name].translation+movement
            q = hip_q@baseline[name].to_quaternion()
        elif name.startswith('spine_'):
            fraction = int(name[-2:])/5.
            q = hip_q.slerp(chest_q, fraction)@baseline[name].to_quaternion()
        elif name.startswith('neck_'):
            # The head trails only part of the turn; do not rotate the gaze by
            # the full sweep arc or add another arm-derived torso transform.
            fraction = .70 if name == 'neck_01' else .52
            q = Quaternion().slerp(chest_q, fraction)@baseline[name].to_quaternion()
        target[name] = matrix(point, q)
        if name.startswith('thigh_'):
            s = name[-1]
            support[s], _ = v18.solve_support_leg(s, target, baseline, legs)
            target[name] = support[s][name]
        elif name.startswith(('calf_', 'foot_')):
            target[name] = support[name[-1]][name]

    for side in ('l', 'r'):
        attacking = side == spec['side']
        donor_side = 'r' if attacking else 'l'
        chain = source_chain(src, neutral, donor_side)
        ref = refs[side]
        amount = active if attacking else active*.24
        # The accepted HundredEyed author aligns its actual source shoulder,
        # elbow and wrist plane with the target neutral, releasing alignment
        # during the strike. Mirror rotations by conjugation, never Euler signs.
        source_frame = chain['upper_frame']
        source_zero = chain['upper0']
        if spec['side'] == 'l':
            # Reflect both segment vectors; their cross product is an axial
            # vector and therefore needs the extra minus sign under reflection.
            source_frame = palm_frame(MIRROR@chain['u'], -(MIRROR@chain['n']))
            source_zero = palm_frame(MIRROR@(chain['upper0']@RIGHT),
                                     -(MIRROR@(chain['upper0']@UP)))
        alignment = ref['upper_frame']@source_zero.inverted()
        alignment = alignment.slerp(Quaternion(), amount)
        desired = alignment@source_frame
        upper, normal = desired@RIGHT, desired@UP
        # Adapt Rampage's behind-the-head windup to M07's anterior shoulder
        # corridor. Rotate the entire elbow plane with the upper arm.
        if attacking:
            original = upper.copy()
            upper.y = min(-.16, upper.y)
            upper.z = clamp(upper.z, -.78, .05)
            upper.normalize()
            normal = original.rotation_difference(upper)@normal
        body = target['spine_05'].to_quaternion()@baseline['spine_05'].to_quaternion().inverted()
        u_local, n_local = body.inverted()@upper, body.inverted()@normal
        swing = ref['u'].rotation_difference(u_local)
        roll = signed_angle(swing@ref['n'], n_local, u_local)
        previous_roll = state.get(side, roll)
        while roll-previous_roll > math.pi:
            roll -= 2.*math.pi
        while roll-previous_roll < -math.pi:
            roll += 2.*math.pi
        state[side] = roll
        roll = bounded(roll, math.radians(28. if attacking else 16.))
        relative = Quaternion(u_local, roll)@swing
        relative = Quaternion().slerp(relative, amount)
        delta = body@relative
        bend = ref['bend']+(chain['bend']-ref['bend'])*amount
        lower_delta = delta@Quaternion(ref['n'], bend-ref['bend'])
        upper_name, lower_name, hand_name = [n+'_'+side for n in ('upperarm', 'lowerarm', 'hand')]
        shoulder = target['clavicle_'+side]@locals_[upper_name].translation
        target[upper_name] = matrix(shoulder, delta@baseline[upper_name].to_quaternion())
        elbow = target[upper_name]@locals_[lower_name].translation
        target[lower_name] = matrix(elbow, lower_delta@baseline[lower_name].to_quaternion())
        wrist = target[lower_name]@locals_[hand_name].translation
        lower_frame = lower_delta@ref['lower_frame']
        residual = wrist_residual(chain, src, neutral, donor_side, amount)
        if spec['side'] == 'l':
            # Reflection changes the handedness of the source anatomical
            # frame. X/Y are polar directions, Z is the elbow-plane normal.
            c = Matrix(((1., 0., 0.), (0., 1., 0.), (0., 0., -1.)))
            residual = (c@residual.to_matrix()@c).to_quaternion()
        hand_q = lower_frame@residual@ref['lower_frame'].inverted()@baseline[hand_name].to_quaternion()
        target[hand_name] = matrix(wrist, hand_q)
        for p in ordered:
            if p.name.endswith('_'+side) and p.name.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')):
                target[p.name] = target[p.parent.name]@locals_[p.name]
    clearance.inherit_gills(target, baseline, ordered)
    return target


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    donor = read_donor('Attack_Biped_Melee_A')
    neutral = read_donor('Idle_Biped')['frames'][0]
    tracks = body_tracks(donor, neutral)
    profile = json.loads(clearance.PROFILE.read_text(encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    rig = v20.original_rig()
    rig.data.pose_position = 'POSE'
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    baseline = v17.cache_action(rig, bpy.data.actions['A_M07_Idle_PalmArmV20'], 1, ordered)[0]
    locals_ = {p.name: baseline[p.parent.name].inverted()@baseline[p.name] if p.parent else baseline[p.name].copy() for p in ordered}
    refs = {s: reference(baseline, s) for s in ('l', 'r')}
    legs = {s: v18.support_reference(baseline, s) for s in ('l', 'r')}
    hidden = {o.name: o.hide_viewport for o in bpy.data.objects if o.type == 'MESH'}
    for name in hidden:
        bpy.data.objects[name].hide_viewport = True
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.
    scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', .01
    manifest = dict(revision='ReferenceChainSweepV26', source=str(OUT/'M07_Original_ReferenceChainSweep_V26.blend'),
        idle_source=str(SOURCE), reference_asset=donor['asset'], reference_sample_hz=donor['fps'],
        reference_json=str(PROJECT/'SourceAssets/HundredEyedSlagMeshy20260930/RampageReferenceIntake/source_motion/Attack_Biped_Melee_A.json'),
        reference_skeleton='/Game/Monsters/BlindSupplicantM07/SK_M07_ReferenceOriginalV11',
        fps=FPS, clips={}, melee_playback_rate=1., contact_window_seconds=.14,
        arm_policy='Current idle calibration; coherent shoulder frame and one elbow hinge; no independent forearm axial rotation',
        wrist_policy='Donor lower-frame-relative delta; wrist swing <=18 degrees, axial <=8 degrees; no forced palm target',
        body_policy='Source hip/chest rotation attenuated and distributed across spine; planted support legs; quiet opposite arm',
        performance_policy='Baked ordinary animation tracks; reuse V25 tissue clearance; no new runtime IK or collision work',
        geometry_modified=False, weights_modified=False, reference_pose_modified=False,
        source_saved=False, animation_fbx_exported=False, ue_imported=False, ue_saved=False,
        tested=False, runtime_tested=False, rendered=False, user_review_pending=True)
    actions = {}
    for role, spec in SPECS.items():
        action = bpy.data.actions.new('A_M07_'+role+'_ReferenceChainSweepV26')
        action.use_fake_user = True
        motion.activate(rig, action)
        count, previous, first = round(spec['duration']*FPS)+1, {}, None
        state = {}
        for index in range(count):
            scene.frame_set(index+1)
            target = pose_at(index/FPS, spec, donor, neutral, tracks, baseline, rest, ordered, refs, legs, locals_, state)
            if index in (0, count-1):
                target = {name: transform.copy() for name, transform in baseline.items()}
            clearance.bake_clearance(target, rest, profile)
            if index == 0:
                first = {name: transform.copy() for name, transform in target.items()}
            elif index == count-1:
                target = first
            running.insert_frame(rig, target, rest, ordered, index+1, previous)
        scene.frame_set(0)
        for p in ordered:
            p.matrix_basis = Matrix.Identity(4)
            for channel in ('location', 'rotation_quaternion', 'scale'):
                p.keyframe_insert(data_path=channel, frame=0, group=p.name)
        for curve in running.curves(action):
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        fbx = OUT/('A_M07_'+role+'.fbx')
        v15.export(rig, action, fbx, count)
        manifest['clips'][role] = dict(role=role, action=action.name, file=str(fbx), fps=FPS, frames=count,
            duration_seconds=spec['duration'], contact_seconds=spec['contact'], loop=False, root_motion=False,
            asset='/Game/Monsters/BlindSupplicantM07/AnimationsReferenceChainSweepV26/A_M07_'+role,
            source_action=donor['asset'], source_time_map=sweep_time_map(spec['contact'], spec['duration']),
            baked_clearance=True, reference_only_blender_frame=0,
            exported_blender_frame_start=1, exported_blender_frame_end=count)
        actions[role] = action
        print('M07_V26_CLIP_EXPORTED '+role+' '+str(fbx), flush=True)
    for name, value in hidden.items():
        bpy.data.objects[name].hide_viewport = value
    motion.activate(rig, actions['SweepRight'])
    scene.frame_start, scene.frame_end = 1, manifest['clips']['SweepRight']['frames']
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=manifest['source'], compress=True)
    manifest.update(source_saved=True, animation_fbx_exported=True)
    (OUT/'reference_chain_sweep_manifest_v26.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('M07_V26_SOURCE_SAVED '+str(OUT), flush=True)


if __name__ == '__main__':
    main()
