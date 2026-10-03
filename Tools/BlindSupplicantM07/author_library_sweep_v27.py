"""Fit the clean native library retarget, without reconstructing its arm joints.

Retains the complete Attack_D body/limb rotations and timing. Fits long-claw
clearance by rotating each whole arm from its shoulder, baked offline. No
independent forearm twist, wrist target, runtime IK, render or gameplay test.
"""
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'LibrarySweepV27/Motion'
SOURCE = ROOT/'PalmArmMotionV20/Motion/M07_Original_PalmArmMotion_V20.blend'
sys.path.insert(0, str(Path(__file__).parent))
import author_motion_v04 as motion
import author_running_v12 as running
import author_locomotion_death_v15 as v15
import author_leg_joint_motion_v17 as v17
import author_palm_arm_motion_v20 as v20
import m07_clearance_v25 as clearance

FPS = 60
RECOVERY_START = 1.0
ACCEPTED = ROOT/'LibrarySweepV27/RecoveryFix/accepted_motion_manifest_v27.json'
UP, RIGHT, FWD = Vector((0.,0.,1.)), Vector((1.,0.,0.)), Vector((0.,-1.,0.))
REFLECT = Matrix(((-1.,0.,0.),(0.,1.,0.),(0.,0.,1.)))
DIGITS = ('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')


def matrix(p, q):
    return Matrix.LocRotScale(p, q, Vector((1.,1.,1.)))


def ease(x):
    x = min(1., max(0., x))
    return x*x*x*(10.-15.*x+6.*x*x)


def side_name(name):
    return name[:-2]+('_r' if name.endswith('_l') else '_l') if name.endswith(('_l','_r')) else name


def body_frame(pose):
    across = (pose['upperarm_l'].translation-pose['upperarm_r'].translation).normalized()
    up = (pose['head'].translation-pose['pelvis'].translation).normalized()
    up = (up-across*up.dot(across)).normalized()
    return Matrix((across, up.cross(across), up)).transposed()


def read_native(record):
    raw = json.loads(Path(record['pose_cache']).read_text(encoding='utf-8'))
    c = Matrix(((1.,0.,0.),(0.,-1.,0.),(0.,0.,1.)))
    def convert(row):
        result = {}
        for name, value in row.items():
            x,y,z,w = value['rotation_xyzw']
            q = (c@Quaternion((w,x,y,z)).to_matrix()@c).to_quaternion()
            result[name] = matrix(c@Vector(value['translation_cm']), q)
        return result
    return convert(raw['reference']), [convert(row) for row in raw['frames']]


def registered_poses(native_rest, samples, rest, ordered):
    registration = body_frame(rest)@body_frame(native_rest).transposed()
    g = registration.to_quaternion()
    # The native pose cache carries centimetres and the pelvis root explicitly.
    # Rebuild target FK with its own bind translations, keeping every limb length.
    name, child = 'upperarm_r', 'lowerarm_r'
    scale = (rest[child].translation-rest[name].translation).length/(samples[0][child].translation-samples[0][name].translation).length
    local = {p.name: rest[p.parent.name].inverted()@rest[p.name] if p.parent else rest[p.name] for p in ordered}
    poses = []
    for raw in samples:
        target = {}
        for p in ordered:
            n = p.name
            q = g@raw[n].to_quaternion()@native_rest[n].to_quaternion().inverted()@g.inverted()@rest[n].to_quaternion()
            point = target[p.parent.name]@local[n].translation if p.parent else rest[n].translation.copy()
            if n == 'pelvis':
                point = rest[n].translation+registration@(raw[n].translation-native_rest[n].translation)*scale
            target[n] = matrix(point, q)
        poses.append(target)
    # Remove only net forward/lateral travel; retain the source's step and
    # vertical load. Gameplay already owns the actor's world movement.
    start, end = poses[0]['pelvis'].translation, poses[-1]['pelvis'].translation
    drift = end-start
    for i, target in enumerate(poses):
        offset = Vector((-start.x-drift.x*i/(len(poses)-1), -start.y-drift.y*i/(len(poses)-1), 0.))
        for n in target:
            if n != 'root':
                target[n].translation += offset
    return poses, scale


def mirror_pose(source, rest, ordered):
    result = {}
    for p in ordered:
        n, other = p.name, side_name(p.name)
        other = other if other in source else n
        delta = source[other].to_quaternion()@rest[other].to_quaternion().inverted()
        q = (REFLECT@delta.to_matrix()@REFLECT).to_quaternion()@rest[n].to_quaternion()
        position = REFLECT@source[other].translation
        if p.parent:
            position = result[p.parent.name]@(rest[p.parent.name].inverted()@rest[n]).translation
        if n == 'pelvis':
            position = REFLECT@source[n].translation
        result[n] = matrix(position, q)
    return result


def pose_blend(source, idle, ordered, amount):
    target = {}
    for p in ordered:
        n, parent = p.name, p.parent.name if p.parent else None
        a = idle[parent].inverted()@idle[n] if parent else idle[n]
        b = source[parent].inverted()@source[n] if parent else source[n]
        # Preserve M07's open claw articulation; the mannequin has human
        # fingers and no retarget chains for the creature's long digits.
        weight = amount[n] if isinstance(amount, dict) else amount
        blend = 0. if n.startswith(DIGITS) or n.startswith('gill_') else weight
        local = matrix(a.translation.lerp(b.translation, blend), a.to_quaternion().slerp(b.to_quaternion(), blend))
        target[n] = target[parent]@local if parent else local
    return target


def recovery_weights(ordered, time, duration):
    # Attack_D settles into a near-static tail around 1.2 s. Begin recovering
    # before that hold, instead of snapping the whole body home in the last .3 s.
    # Keep the accepted windup, contact and follow-through through 1.0 s intact.
    result = {}
    for bone in ordered:
        name = bone.name
        delay = (.18 if name.startswith('hand_') else
                 .12 if name.startswith(('upperarm_', 'lowerarm_')) else
                 .10 if name.startswith(('neck_', 'head')) else
                 .08 if name.startswith('clavicle_') else
                 .02*int(name[-2:]) if name.startswith('spine_') else 0.)
        start = RECOVERY_START+delay
        result[name] = ease(time/.14)*(1.-ease((time-start)/(duration-start)))
    return result


def body_envelope(rig, rest):
    points = []
    torso = {'pelvis', 'spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05'}
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or obj.name != 'M07_OriginalBody_Display':
            continue
        groups = {g.index for g in obj.vertex_groups if g.name in torso}
        if not groups:
            continue
        to_rig = rig.matrix_world.inverted()@obj.matrix_world
        for v in obj.data.vertices:
            if sum(g.weight for g in v.groups if g.group in groups) > .70:
                points.append(to_rig@v.co)
    verts = np.asarray(points, dtype=np.float64)
    low, high = rest['pelvis'].translation.z, rest['spine_05'].translation.z
    verts = verts[(verts[:,2] >= low-5.) & (verts[:,2] <= high+5.)]
    half_shoulder = (rest['upperarm_l'].translation-rest['upperarm_r'].translation).length*.5
    core = np.array(rest['pelvis'].translation)
    spine = np.array(rest['spine_05'].translation)-core
    fraction = np.clip((verts[:,2]-low)/(high-low), 0., 1.)
    relative = verts-(core+fraction[:,None]*spine)
    # The retained body includes rigid membrane attachments. Fit the central
    # torso separately; those lateral/rear tissues already have their own
    # V25 surface-clearance layer and are not a 2 m wide human chest.
    relative = relative[(np.abs(relative[:,0]) <= half_shoulder*.84) &
                        (relative[:,1] <= half_shoulder*.50)]
    # Conservative torso cross-section from retained body vertices, excluding
    # separate back tissue and arm groups. Long claws get their own thickness.
    radii = np.percentile(np.abs(relative[:,:2]), 99., axis=0)+2.
    return dict(x_cm=float(radii[0]), y_cm=float(radii[1]), z_cm=22.,
                body_vertex_count=len(relative), method='Central retained display-body vertices inside shoulder corridor; 99th percentile plus 2 cm; back tissues handled separately')


def foot_support_samples(rig, rest):
    """Cache the displayed feet's bind-space skinning inputs for baking only."""
    obj = bpy.data.objects['M07_OriginalBody_Display']
    names = {g.index: g.name for g in obj.vertex_groups if g.name in rest}
    feet = {'foot_l', 'ball_l', 'foot_r', 'ball_r'}
    to_rig = rig.matrix_world.inverted()@obj.matrix_world
    coords, weights = [], []
    for vertex in obj.data.vertices:
        row = {names[g.group]: g.weight for g in vertex.groups if g.group in names}
        if sum(w for n, w in row.items() if n in feet) < .5:
            continue
        point = to_rig@vertex.co
        coords.append((*point, 1.))
        total = sum(row.values())
        weights.append({n: w/total for n, w in row.items()})
    points = np.asarray(coords)
    inputs = {}
    for name in set().union(*(row.keys() for row in weights)):
        w = np.array([row.get(name, 0.) for row in weights])
        inputs[name] = (points@np.array(rest[name].inverted()).T)*w[:, None]
    return inputs, len(points)


def support_height(pose, inputs):
    # Restrict to skinned feet: a low hand, claw or hanging back membrane must
    # never lift the character or decide the ground height.
    heights = sum(points@np.array(pose[name])[2, :]
                  for name, points in inputs.items())
    return float(np.min(heights))


def ground_pose(pose, inputs, floor):
    dz = floor-support_height(pose, inputs)
    for value in pose.values():
        position = value.translation.copy()
        position.z += dz
        value.translation = position
    return dz


def arm_samples(pose, side):
    points, radii = [], []
    for a, b, radius, start in [('upperarm','lowerarm',9.,.5), ('lowerarm','hand',8.,0.),
            ('hand','middle_01',10.,0.), ('middle_01','middle_03',9.,0.),
            ('hand','index_03',7.,.35), ('hand','pinky_03',7.,.35), ('thumb_01','thumb_03',7.,0.)]:
        pa, pb = pose[a+'_'+side].translation, pose[b+'_'+side].translation
        for alpha in np.linspace(start, 1., 4):
            points.append(pa.lerp(pb, float(alpha)))
            radii.append(radius)
    return np.asarray(points), np.asarray(radii)


def arm_clearance_path(poses, rest, side, envelope, fixed_prefix, smooth_start=RECOVERY_START):
    # Search only whole-arm shoulder swing. Native elbow/forearm/wrist local
    # rotations remain untouched by this fit, including during the strike.
    sign = 1. if side == 'l' else -1.
    angles = np.array([(out, forward) for out in range(0,33,2) for forward in range(0,49,4)], dtype=float)
    rotations = [Quaternion(FWD, math.radians(sign*a))@Quaternion(RIGHT, math.radians(-b)) for a,b in angles]
    penalty = .018*angles[:,0]**2+.012*angles[:,1]**2
    changes = .10*np.sum((angles[:,None,:]-angles[None,:,:])**2, axis=2)
    previous, predecessors, world_rots = None, [], []
    for index, pose in enumerate(poses):
        body = pose['spine_05'].to_quaternion()@rest['spine_05'].to_quaternion().inverted()
        world = [body@q@body.inverted() for q in rotations]
        world_rots.append(world)
        mats = np.array([q.to_matrix() for q in world])
        shoulder = np.asarray(pose['upperarm_'+side].translation)
        points, thickness = arm_samples(pose, side)
        moved = np.einsum('kij,pj->kpi', mats, points-shoulder)+shoulder
        basis = np.array(body.to_matrix())
        local = np.einsum('kpi,ij->kpj', moved-np.array(pose['pelvis'].translation), basis)
        tip = np.array(body.inverted()@(pose['spine_05'].translation-pose['pelvis'].translation))
        radii = np.stack((envelope['x_cm']+thickness, envelope['y_cm']+thickness, envelope['z_cm']+thickness), axis=-1)
        scaled, axis = local/radii, tip/radii
        t = np.clip(np.sum(scaled*axis, axis=-1)/np.sum(axis*axis, axis=-1), 0., 1.)
        dist = np.linalg.norm(scaled-t[:,:,None]*axis, axis=-1)
        penetration = np.maximum(0., 1.-dist)*np.min(radii, axis=-1)
        # Include the face: the library has an overhead windup before its
        # diagonal sweep, while M07's claws extend well beyond its hand bone.
        head = np.asarray(pose['head'].translation)
        head_pen = np.maximum(0., 17.+thickness-np.linalg.norm(moved-head, axis=-1))
        cost = penalty+40.*np.sum(penetration**2+head_pen**2, axis=-1)
        if index < len(fixed_prefix):
            # The new recovery must not change the already accepted strike
            # via the backward pass of this whole-clip optimization.
            matches = np.all(angles == np.asarray(fixed_prefix[index]), axis=1)
            cost[~matches] += 1.e10
        if index in (0,len(poses)-1):
            cost[1:] += 1.e10
        if previous is None:
            previous = cost
            predecessors.append(np.zeros(len(angles), dtype=int))
        else:
            total = previous[:,None]+changes
            picks = np.argmin(total, axis=0)
            previous = cost+total[picks, np.arange(len(angles))]
            predecessors.append(picks)
    selected, at = [], int(np.argmin(previous))
    for index in reversed(range(len(poses))):
        selected.append(at)
        at = int(predecessors[index][at])
    selected.reverse()
    fitted = angles[selected].copy()
    filtered = np.stack([np.convolve(np.pad(fitted[:,axis], (2,2), mode='edge'),
                        np.array([1.,4.,6.,4.,1.])/16., mode='valid') for axis in (0,1)], axis=1)
    for index in range(len(fixed_prefix), len(poses)):
        weight = ease((index/FPS-smooth_start)/.12)
        fitted[index] += (filtered[index]-fitted[index])*weight
    fitted[-1] = 0.
    owned = ['upperarm_'+side, 'lowerarm_'+side, 'hand_'+side]
    owned += [n for n in poses[0] if n.startswith(DIGITS) and n.endswith('_'+side)]
    for index, pose in enumerate(poses):
        body = pose['spine_05'].to_quaternion()@rest['spine_05'].to_quaternion().inverted()
        out, forward = fitted[index]
        q = body@(Quaternion(FWD, math.radians(sign*out))@Quaternion(RIGHT, math.radians(-forward)))@body.inverted()
        shoulder = pose['upperarm_'+side].translation.copy()
        for n in owned:
            m = pose[n]
            pose[n] = matrix(shoulder+q@(m.translation-shoulder), q@m.to_quaternion())
    return fitted.tolist()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    record = json.loads((ROOT/'LibrarySweepV27/native_retarget_v27.json').read_text(encoding='utf-8'))
    accepted = json.loads(ACCEPTED.read_text(encoding='utf-8'))
    native_rest, samples = read_native(record)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    rig = v20.original_rig()
    rig.data.pose_position = 'POSE'
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    rest = {b.name:b.matrix_local.copy() for b in rig.data.bones}
    idle = v17.cache_action(rig, bpy.data.actions['A_M07_Idle_PalmArmV20'], 1, ordered)[0]
    foot_inputs, foot_count = foot_support_samples(rig, rest)
    floor = support_height(idle, foot_inputs)
    raw, scale = registered_poses(native_rest, samples, rest, ordered)
    envelope = body_envelope(rig, rest)
    profile = json.loads(clearance.PROFILE.read_text(encoding='utf-8'))
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.
    scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', .01
    hidden = {o.name:o.hide_viewport for o in bpy.data.objects if o.type == 'MESH'}
    for name in hidden:
        bpy.data.objects[name].hide_viewport = True
    # Actual source motion determines the attacking side, not asset naming.
    travel = {s:sum((raw[i]['hand_'+s].translation-raw[i-1]['hand_'+s].translation).length
                   for i in range(round(.38*FPS),round(.75*FPS))) for s in ('l','r')}
    source_side = max(travel, key=travel.get)
    duration, actions = record['duration_seconds'], {}
    manifest = dict(revision='LibrarySweepV27', source=str(OUT/'M07_LibrarySweep_V27.blend'),
        source_asset=record['source'], native_retargeter=record['retargeter'], native_asset=record['raw_asset'],
        source_attacking_side=source_side, fps=FPS, reference_skeleton='/Game/Monsters/BlindSupplicantM07/SK_M07_ReferenceOriginalV11',
        source_duration_seconds=duration, source_to_blender_position_scale=scale, body_envelope=envelope,
        root_policy=record['root_policy'], grounding_revision='V27PelvisGroundingFix',
        recovery_revision='V27ContinuousRecovery', accepted_attack_end_seconds=RECOVERY_START,
        accepted_attack_manifest=str(ACCEPTED),
        recovery_policy='Continuous return from 1.0 s, pelvis/chest then shoulder/arm/wrist; quintic local-space fade with smooth shoulder fit; accepted strike prefix locked',
        grounding_policy='Retarget pelvis without ground-root overwrite; bake vertical support from displayed skinned feet at current idle floor; retain source joint rotations and steps',
        support_vertex_count=foot_count, idle_support_floor_cm=floor,
        policy='Complete native library retarget; original timing; whole-arm shoulder clearance; no independently authored elbow or forearm twist',
        geometry_modified=False, weights_modified=False, reference_pose_modified=False, new_runtime_ik=False,
        clips={}, melee_playback_rate=1., contact_window_seconds=.20, source_saved=False,
        animation_fbx_exported=False, ue_imported=False, ue_saved=False,
        tested=False, runtime_tested=False, rendered=False, user_review_pending=True)
    for role, side in (('SweepLeft','l'),('SweepRight','r')):
        poses = []
        for index, pose in enumerate(raw):
            t = index/FPS
            src = pose if side == source_side else mirror_pose(pose, rest, ordered)
            poses.append(pose_blend(src, idle, ordered, recovery_weights(ordered, t, duration)))
        ground_offsets = [ground_pose(pose, foot_inputs, floor) for pose in poses]
        prefix = accepted['clips'][role]['shoulder_fit_degrees']
        corrections = {s:arm_clearance_path(poses, rest, s, envelope,
            prefix[s][:round(RECOVERY_START*FPS)+1]) for s in ('l','r')}
        action = bpy.data.actions.new('A_M07_'+role+'_LibrarySweepV27')
        action.use_fake_user = True
        motion.activate(rig, action)
        previous = {}
        for index, pose in enumerate(poses):
            scene.frame_set(index+1)
            clearance.inherit_gills(pose, idle, ordered)
            clearance.bake_clearance(pose, rest, profile)
            running.insert_frame(rig, pose, rest, ordered, index+1, previous)
        scene.frame_set(0)
        for p in ordered:
            p.matrix_basis = Matrix.Identity(4)
            for prop in ('location','rotation_quaternion','scale'):
                p.keyframe_insert(data_path=prop, frame=0, group=p.name)
        for curve in running.curves(action):
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        fbx = OUT/('A_M07_'+role+'.fbx')
        v15.export(rig, action, fbx, len(poses))
        manifest['clips'][role] = dict(role=role, action=action.name, file=str(fbx), frames=len(poses),
            duration_seconds=duration, contact_seconds=.60, loop=False, root_motion=False,
            asset='/Game/Monsters/BlindSupplicantM07/AnimationsLibrarySweepV27/A_M07_'+role,
            source_asset=record['source'], mirrored=side != source_side, shoulder_fit_degrees=corrections,
            baked_foot_support_offset_cm=ground_offsets,
            source_timing_preserved=True, exported_blender_frame_start=1, exported_blender_frame_end=len(poses))
        actions[role] = action
        print('M07_V27_LIBRARY_CLIP_EXPORTED '+role, flush=True)
    for name, value in hidden.items():
        bpy.data.objects[name].hide_viewport = value
    motion.activate(rig, actions['SweepRight'])
    scene.frame_start, scene.frame_end = 1, len(raw)
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=manifest['source'], compress=True)
    manifest.update(source_saved=True, animation_fbx_exported=True)
    (OUT/'library_sweep_manifest_v27.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('M07_V27_LIBRARY_SOURCE_SAVED '+str(OUT), flush=True)


if __name__ == '__main__':
    main()
