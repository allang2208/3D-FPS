"""Restore M07's original two-leg reference and author bounded biped feet.

The canine reference contributed lift/recovery/support timing only. V07's
additional hocks and upper-knee relocation are withdrawn. This source module
never replaces the original visible mesh and never starts a renderer or UE.
"""
from pathlib import Path
import argparse
import json
import math

import numpy as np

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT / 'RecoveryOriginalV08/legs'
REFERENCE = ROOT / 'RecoveryOriginalV06/rig_motion/original_rig_guides.json'
CHAIN = ('thigh', 'calf', 'foot', 'ball')
LEG_NAMES = [base+'_'+side for side in ('l', 'r') for base in CHAIN]
FLOOR_ROLES = ('Idle', 'WallListen', 'MeleeLeft', 'MeleeRight', 'Hit', 'Dizzy')


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def smooth(value):
    value = np.clip(value, 0., 1.)
    return value*value*value*(value*(value*6.-15.)+10.)


def anatomy():
    """Publish the exact V06 original-source joints, parents and bone frames."""
    source = json.loads(REFERENCE.read_text(encoding='utf-8'))
    record = {
        'revision': 'OriginalV08', 'reference_source': str(REFERENCE),
        'visible_geometry_source': str(ROOT/'Original/Meshy_AI_Veilwing_07_1001123357_texture.glb'),
        'chain': list(CHAIN), 'removed_deform_bones': ['hock_l', 'hock_r'],
        'bone_heads_cm': {n: source['bone_heads_cm'][n] for n in LEG_NAMES},
        'bone_tails_cm': {n: source['bone_tails_cm'][n] for n in LEG_NAMES},
        'bone_reference_matrices_cm': {n: source['bone_reference_matrices_cm'][n] for n in LEG_NAMES},
        'parents': {n: source['parents'][n] for n in LEG_NAMES},
        'joint_guides_source': {n: source['joint_guides_source'][n] for n in LEG_NAMES
                                if n in source['joint_guides_source']},
        'foot_forward_blender': [0., -1., 0.],
        'bend_plane': 'Derived separately for each side from original hip, knee and ankle positions, then transported with the pelvis.',
        'motion_method': 'Mature two-foot Walk trajectory in the existing clean authoring module; source-local rotations are not copied from a canine chain. Original toe-to-ankle support offset and bounded foot roll are preserved.',
        'foot_limits_degrees': {'locomotion_pitch': [-18., 28.], 'locomotion_roll': [-8., 8.],
                               'locomotion_yaw': [-12., 12.], 'recovery_local_pitch': [-60., 75.],
                               'recovery_local_roll': [-12., 12.], 'recovery_local_yaw': [-18., 18.],
                               'toe_local_pitch': [-18., 30.]},
        'gait_contract': {'SlowWalk': {'duration_seconds': 50/30, 'speed_cm_s': 90},
                          'Chase': {'duration_seconds': 36/30, 'speed_cm_s': 145}},
        'source_geometry_changed': False, 'tested': False, 'rendered': False,
        'runtime_sampled': False, 'user_accepted': False,
    }
    write_json(OUT/'biped_leg_reference_v08.json', record)
    return record


def apply_reference(rig, unit_scale=1):
    """Before authoring actions: metre rig=1; native centimetre rig=100.

    Restore V06 matrices exactly, including each side's bone roll convention.
    The original connected joint positions are not inferred from bone tails:
    imported humanoid bone display axes and child joint offsets differ.
    """
    import bpy
    from mathutils import Matrix, Vector
    record = anatomy()
    bpy.context.view_layer.objects.active = rig
    if rig.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='EDIT')
    bones = rig.data.edit_bones
    for side in ('l', 'r'):
        hock = bones.get('hock_'+side)
        if hock is not None:
            for child in list(hock.children):
                child.parent = bones.get('calf_'+side)
            bones.remove(hock)
    factor = float(unit_scale)/100.
    for name in LEG_NAMES:
        bone = bones.get(name) or bones.new(name)
        matrix = Matrix(record['bone_reference_matrices_cm'][name])
        matrix.translation *= factor
        bone.matrix = matrix
        a = Vector(record['bone_heads_cm'][name])*factor
        b = Vector(record['bone_tails_cm'][name])*factor
        bone.length = (b-a).length
        bone.use_connect = False
        bone.use_deform = True
    for name in LEG_NAMES:
        bones[name].parent = bones[record['parents'][name]]
    bpy.ops.object.mode_set(mode='OBJECT')
    for name in LEG_NAMES:
        pose = rig.pose.bones[name]
        pose.rotation_mode = 'QUATERNION'
        pose.matrix_basis = Matrix.Identity(4)
    rig['leg_reference_revision'] = 'OriginalV08 original four-bone biped chain; V07 hocks removed'
    return record


def _basis(rig):
    from mathutils import Vector
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    data = {}
    for side in ('l', 'r'):
        names = [base+'_'+side for base in CHAIN]
        hip, knee, ankle, ball = [rest[n].translation.copy() for n in names]
        axis = (ankle-hip).normalized()
        bend = knee-hip-axis*(knee-hip).dot(axis)
        # Only a numerical fallback; the supplied source reference is bent.
        if bend.length < 1.e-8:
            bend = Vector((0., 1., 0.))
            bend -= axis*bend.dot(axis)
        data[side] = {'hip': hip, 'knee': knee, 'ankle': ankle, 'ball': ball,
                      'lengths': ((knee-hip).length, (ankle-knee).length),
                      'bend': bend.normalized(),
                      'upper_direction': (knee-hip).normalized(),
                      'lower_direction': (ankle-knee).normalized(),
                      'ankle_to_ball_local': rest[names[2]].to_quaternion().inverted()@(ball-ankle)}
    return rest, data


def _bounded_world_foot(quaternion, reference, pitch=(-18., 28.), roll=(-8., 8.), yaw=(-12., 12.), frame=None):
    """Anatomical sagittal roll in the creature frame, never a dog bone frame."""
    delta = quaternion@reference.inverted()
    if frame is not None:
        delta = frame.inverted()@delta@frame
    if delta.w < 0:
        delta.negate()
    angles = delta.to_euler('XYZ')
    limits = (pitch, roll, yaw)
    for i, (lo, hi) in enumerate(limits):
        angles[i] = max(math.radians(lo), min(math.radians(hi), angles[i]))
    result = angles.to_quaternion()
    if frame is not None:
        result = frame@result@frame.inverted()
    return result@reference


def _solve(rig, target, rest, side_data, side, endpoint, pelvis_delta, factor):
    """Two-bone original knee plane; explicit parent frames prevent tearing."""
    from mathutils import Vector, Matrix
    names = [base+'_'+side for base in CHAIN]
    hip = target[names[0]].translation.copy()
    info = side_data[side]
    l1, l2 = info['lengths']
    axis = endpoint-hip
    if axis.length < 1.e-8:
        axis = Vector((0., 0., -1.))
    distance = max(abs(l1-l2)+.0005*factor,
                   min(axis.length, l1+l2-.0005*factor))
    axis.normalize()
    # The anatomical plane comes from this original leg, rather than the
    # donor's knee or an invented forward-knee/posterior-hock pair.
    bend = pelvis_delta@info['bend']
    bend -= axis*bend.dot(axis)
    if bend.length < 1.e-8:
        bend = info['bend']-axis*info['bend'].dot(axis)
    if bend.length < 1.e-8:
        bend = Vector((1., 0., 0.))
        bend -= axis*bend.dot(axis)
    bend.normalize()
    along = (l1*l1-l2*l2+distance*distance)/(2.*distance)
    knee = hip+axis*along+bend*math.sqrt(max(0., l1*l1-along*along))
    ankle = hip+axis*distance
    upper = (knee-hip).normalized()
    lower = (ankle-knee).normalized()
    # Transport both direction and hinge plane. Arbitrary Epic bone display
    # axes never define the limb's anatomical bend or its roll orientation.
    source_hinge = info['upper_direction'].cross(info['lower_direction']).normalized()
    target_hinge = upper.cross(lower).normalized()
    def geometric_frame(direction, hinge):
        transverse = hinge.cross(direction).normalized()
        return Matrix((direction, transverse, hinge)).transposed()
    for name, a, direction, ref_direction in (
            (names[0], hip, upper, info['upper_direction']),
            (names[1], knee, lower, info['lower_direction'])):
        delta = geometric_frame(direction, target_hinge)@geometric_frame(ref_direction, source_hinge).transposed()
        rotation = delta.to_quaternion()@rest[name].to_quaternion()
        matrix = rotation.to_matrix().to_4x4()
        matrix.translation = a
        target[name] = matrix
    return ankle


def install_motion_hooks(motion_module):
    """Install before motion_module.author(); preserve all source choreography.

    Walk endpoints continue to come from the existing mature biped source's
    common-travel-removed ball tracks, scaled to the unchanged 90/145 cm/s.
    """
    from mathutils import Matrix
    original_leg = motion_module.Author.leg
    if getattr(original_leg, '_m07_original_v08', False):
        return

    def leg(author, side, endpoint, foot_q, raw=None):
        rig = author.rig
        local_rest, data = _basis(rig)
        # The maker keeps world references. This project's rig object is an
        # identity transform; all other conversion still uses its inverse.
        target = {p.name: motion_module.world(rig, p.name) for p in author.ordered}
        pelvis_delta = target['pelvis'].to_quaternion()@author.rest['pelvis'].to_quaternion().inverted()
        reference_q = author.rest['foot_'+side].to_quaternion()
        toe = endpoint+foot_q@data[side]['ankle_to_ball_local']
        foot_q = _bounded_world_foot(foot_q, reference_q)
        endpoint = toe-foot_q@data[side]['ankle_to_ball_local']
        ankle = _solve(rig, target, author.rest, data, side, endpoint, pelvis_delta, 1.)
        foot_name = 'foot_'+side
        foot_matrix = foot_q.to_matrix().to_4x4()
        foot_matrix.translation = ankle
        target[foot_name] = foot_matrix
        ball_name = 'ball_'+side
        foot_delta = foot_q@reference_q.inverted()
        ball_matrix = (foot_delta@author.rest[ball_name].to_quaternion()).to_matrix().to_4x4()
        ball_matrix.translation = ankle+foot_q@data[side]['ankle_to_ball_local']
        target[ball_name] = ball_matrix
        inv = rig.matrix_world.inverted()
        for name in [base+'_'+side for base in CHAIN]:
            pose = rig.pose.bones[name]
            kwargs = {'parent_matrix': inv@target[pose.parent.name],
                      'parent_matrix_local': pose.parent.bone.matrix_local} if pose.parent else {}
            pose.matrix_basis = pose.bone.convert_local_to_pose(inv@target[name], pose.bone.matrix_local,
                                                                invert=True, **kwargs)
            pose.rotation_mode = 'QUATERNION'
            pose.location = (0., 0., 0.)
            pose.scale = (1., 1., 1.)
        motion_module.update()

    leg._m07_original_v08 = True
    motion_module.Author.leg = leg


def _curves(action):
    return action.fcurves if not action.is_action_layered else [c for layer in action.layers
        for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves]


def apply_motion(rig, action, name, fps=30, unit_scale=1):
    """Reauthor feet/knees on a freshly generated four-bone action.

    For locomotion use the current biped toe trajectories and retain their
    timing. For standing states support each original forefoot centre. Falling
    and getting-up keep source leg choreography and bound ankle articulation
    in the transported lower-leg frame, so a tilted body can still recover.
    This method works whether or not install_motion_hooks was called.
    """
    import bpy
    from mathutils import Vector, Matrix
    role = name.removeprefix('A_M07_')
    rig.animation_data_create()
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]
    for track in rig.animation_data.nla_tracks:
        track.mute = True
    rest, side_data = _basis(rig)
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    endpoints = [float(k.co.x) for c in _curves(action) for k in c.keyframe_points if k.co.x >= 1.]
    end = int(round(max(endpoints)))
    locomotion = role in ('SlowWalk', 'Chase')
    standing = role in FLOOR_ROLES
    previous = {}
    for frame in range(1, end+1):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        target = {p.name: p.matrix.copy() for p in ordered}
        pelvis_delta = target['pelvis'].to_quaternion()@rest['pelvis'].to_quaternion().inverted()
        for side in ('l', 'r'):
            names = [base+'_'+side for base in CHAIN]
            foot_name, ball_name = names[2:]
            foot_ref = rest[foot_name].to_quaternion()
            ball_ref = rest[ball_name].to_quaternion()
            if locomotion or standing:
                toe = target[ball_name].translation.copy() if locomotion else rest[ball_name].translation.copy()
                foot_q = _bounded_world_foot(target[foot_name].to_quaternion(), foot_ref) if locomotion else foot_ref
                endpoint = toe-foot_q@side_data[side]['ankle_to_ball_local']
                ankle = _solve(rig, target, rest, side_data, side, endpoint, pelvis_delta, unit_scale)
                target[foot_name] = foot_q.to_matrix().to_4x4()
                target[foot_name].translation = ankle
                foot_delta = foot_q@foot_ref.inverted()
                # Toe flexion follows the source but cannot fold the supporting
                # digit pad behind the heel or rotate it as a canine hock.
                expected_ball = foot_delta@ball_ref
                toe_q = _bounded_world_foot(target[ball_name].to_quaternion(), expected_ball,
                                              pitch=(-18., 30.), roll=(-5., 5.), yaw=(-5., 5.))
                target[ball_name] = toe_q.to_matrix().to_4x4()
                target[ball_name].translation = ankle+foot_q@side_data[side]['ankle_to_ball_local']
            else:
                # Recovery is evaluated relative to the calf; global upright
                # limits would flatten feet unnaturally while lying down.
                calf_delta = target[names[1]].to_quaternion()@rest[names[1]].to_quaternion().inverted()
                transported_foot = calf_delta@foot_ref
                foot_q = _bounded_world_foot(target[foot_name].to_quaternion(), transported_foot,
                                               pitch=(-60., 75.), roll=(-12., 12.), yaw=(-18., 18.), frame=calf_delta)
                ankle = target[foot_name].translation.copy()
                target[foot_name] = foot_q.to_matrix().to_4x4()
                target[foot_name].translation = ankle
                foot_delta = foot_q@foot_ref.inverted()
                expected_ball = foot_delta@ball_ref
                toe_q = _bounded_world_foot(target[ball_name].to_quaternion(), expected_ball,
                                              pitch=(-18., 30.), roll=(-5., 5.), yaw=(-5., 5.), frame=foot_delta)
                target[ball_name] = toe_q.to_matrix().to_4x4()
                target[ball_name].translation = ankle+foot_q@side_data[side]['ankle_to_ball_local']
        for pose in ordered:
            if pose.name not in LEG_NAMES:
                continue
            kwargs = {'parent_matrix': target[pose.parent.name],
                      'parent_matrix_local': pose.parent.bone.matrix_local} if pose.parent else {}
            pose.matrix_basis = pose.bone.convert_local_to_pose(target[pose.name], pose.bone.matrix_local,
                                                               invert=True, **kwargs)
            pose.rotation_mode = 'QUATERNION'
            pose.location = Vector()
            pose.scale = Vector((1., 1., 1.))
            q = pose.rotation_quaternion.copy()
            if pose.name in previous and q.dot(previous[pose.name]) < 0:
                q.negate()
                pose.rotation_quaternion = q
            previous[pose.name] = q
            for prop in ('location', 'rotation_quaternion', 'scale'):
                pose.keyframe_insert(data_path=prop, frame=frame, group=pose.name)
    for name in LEG_NAMES:
        pose = rig.pose.bones[name]
        pose.matrix_basis = Matrix.Identity(4)
        for prop in ('location', 'rotation_quaternion', 'scale'):
            pose.keyframe_insert(data_path=prop, frame=0, group=name)
    for curve in _curves(action):
        if any(curve.data_path.startswith('pose.bones["'+n+'"]') for n in LEG_NAMES):
            for point in curve.keyframe_points:
                point.interpolation = 'LINEAR'
    record = {'revision': 'OriginalV08', 'role': role, 'action': action.name,
        'fps': fps, 'frames': end, 'duration_seconds': (end-1)/fps,
        'speed_cm_s': 90 if role == 'SlowWalk' else 145 if role == 'Chase' else 0,
        'leg_chain': list(CHAIN), 'reference_source': str(REFERENCE),
        'method': 'Original four-bone biped reference; native projected knee plane; bounded foot and toe articulation; source biped trajectory preserved.',
        'body_hand_gill_curves_replaced': False, 'tested': False, 'rendered': False,
        'runtime_sampled': False}
    write_json(OUT/'actions'/f'{role}_biped_authoring.json', record)
    bpy.context.scene.frame_set(0)
    return record


def make_weights(final_rig_guides, region_path=None, output_path=None):
    """Produce normalized source-ID rows for legs only, with a coherent pad.

    Skin support is fitted to joint-head segments, not imported bone display
    axes. Every foot/heel/pad row excludes calf/thigh weights; UV-seam copies
    share the same coordinate field. Body, hands and original gills are kept.
    """
    source = np.load(ROOT/'Authoring/source_mesh.npz')
    raw = source['positions'].astype(np.float64)
    faces = source['indices'].reshape(-1, 3)
    region_path = Path(region_path or ROOT/'RecoveryOriginalV06/regions/source_regions_original_v06.npz')
    labels = np.load(region_path)['face_labels']
    body_ids = np.unique(faces[labels == 0])
    guides = json.loads(Path(final_rig_guides).read_text(encoding='utf-8'))
    heads = {n: np.asarray(v, dtype=np.float64) for n, v in guides['bone_heads_cm'].items()}
    scale = 310./(raw[:, 1].max()-raw[:, 1].min())
    points = np.c_[raw[:, 0], -raw[:, 2], raw[:, 1]-raw[:, 1].min()]*scale
    names = ['pelvis']+[base+'_'+side for side in ('l', 'r') for base in CHAIN]
    rows, fields = [], []
    for side, sign in (('l', 1), ('r', -1)):
        ids = body_ids[(raw[body_ids, 0]*sign > .001) & (raw[body_ids, 1] < -.130)]
        q = points[ids]
        side_names = [base+'_'+side for base in CHAIN]
        joints = [heads[n] for n in side_names]
        lengths = np.asarray([np.linalg.norm(b-a) for a, b in zip(joints, joints[1:])])
        knots = np.r_[0., np.cumsum(lengths)]
        candidates = []
        for a, b, length in zip(joints, joints[1:], lengths):
            t = np.clip((q-a)@(b-a)/max(length*length, 1.e-12), 0., 1.)
            distance = np.linalg.norm(q-a-t[:, None]*(b-a), axis=1)
            candidates.append((t, distance))
        segment = np.argmin(np.stack([item[1] for item in candidates], axis=1), axis=1)
        arc = np.empty(len(ids))
        for i, (t, _) in enumerate(candidates):
            selected = segment == i
            arc[selected] = knots[i]+t[selected]*lengths[i]
        field = np.zeros((len(ids), len(names)), dtype=np.float32)
        offset = 1+(0 if side == 'l' else len(CHAIN))
        field[np.arange(len(ids)), offset+segment] = 1.
        for i, halfwidth in ((1, 8.), (2, 6.5), (3, 5.5)):
            selected = np.abs(arc-knots[i]) < halfwidth
            alpha = smooth((arc[selected]-knots[i]+halfwidth)/(2.*halfwidth))
            field[selected] = 0.
            field[selected, offset+i-1] = 1.-alpha
            field[selected, offset+i] = alpha
        # The generated digits fan out horizontally and their nearest bone is
        # often the shin. Source-height and longitudinal forefoot coordinates
        # keep the full plantar support together as foot/ball, including heels.
        plantar = raw[ids, 1] < -.697
        alpha = smooth((raw[ids[plantar], 2]-.012)/.078)
        field[plantar] = 0.
        field[plantar, offset+2] = 1.-alpha
        field[plantar, offset+3] = alpha
        # Ankle transition uses its original height rather than a second hock.
        ankle_band = (raw[ids, 1] >= -.697) & (raw[ids, 1] < -.633)
        alpha = smooth((-.633-raw[ids[ankle_band], 1])/.064)
        ankle_original = field[ankle_band].copy()
        foot_field = np.zeros_like(ankle_original)
        foot_field[:, offset+2] = 1.
        field[ankle_band] = ankle_original*(1.-alpha[:, None])+foot_field*alpha[:, None]
        attachment = smooth((-.130-raw[ids, 1])/.075)
        field *= attachment[:, None]
        field[:, 0] = 1.-attachment
        rows.append(ids)
        fields.append(field)
    ids = np.concatenate(rows)
    field = np.concatenate(fields)
    indices = np.argsort(-field, axis=1)[:, :4]
    sparse = np.take_along_axis(field, indices, axis=1)
    sparse /= sparse.sum(axis=1, keepdims=True)
    output_path = Path(output_path or OUT/'leg_weights_v08.npz')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_path, source_vertex_ids=ids.astype(np.int32),
                        bone_names=np.asarray(names), bone_indices=indices.astype(np.int16),
                        weights=sparse.astype(np.float32))
    write_json(output_path.with_suffix('.json'), {
        'revision': 'OriginalV08', 'source_vertex_rows': len(ids), 'bone_names': names,
        'source_mesh': str(ROOT/'Authoring/source_mesh.npz'),
        'rig_guides': str(final_rig_guides), 'source_regions': str(region_path),
        'removed_influences': ['hock_l', 'hock_r'], 'maximum_influences': 4,
        'method': 'Original biped joint-head chain; source-side fields; finite knee/ankle/ball blends; coherent heel/pad; normalized original vertex IDs.',
        'joint_blend_halfwidth_cm': {'knee': 8., 'ankle': 6.5, 'forefoot': 5.5},
        'non_leg_rows_replaced': False, 'tested': False, 'rendered': False,
    })
    return str(output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rig-guides', default=str(REFERENCE))
    parser.add_argument('--regions')
    args = parser.parse_args()
    anatomy()
    print(make_weights(args.rig_guides, region_path=args.regions))
    print('M07_ORIGINAL_V08_BIPED_SOURCE_SAVED '+str(OUT/'biped_leg_reference_v08.json'))
