"""Author alternating pistol whips and finger-pivot recovery from video study.

Blender --background --python author_actions.py -- M1911|DW715
Uses the existing NaturalAimV3 meshes, grip and mechanics; exports animation only.
No rendering, probes or runtime tests are performed.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

OUT = Path(__file__).parent
BASE = OUT.parent
REVISION = 'VideoRefV3'
SOURCE = BASE.parent / 'PistolDualWield20260914' / 'NaturalAimV3'
MOTION = json.loads((OUT / 'motion.json').read_text(encoding='utf-8'))
WEAPON = sys.argv[sys.argv.index('--') + 1]
RIG_NAME = {'M1911': 'SK_M1911_Manny', 'DW715': 'SK_DW715_Manny'}[WEAPON]


def camera(v):
    return Vector((-v[1], -v[0], v[2]))


def turn(angles):
    pitch, yaw, roll = angles
    return Euler(tuple(math.radians(v) for v in (-pitch, -roll, -yaw)), 'XYZ').to_quaternion()


def source_keyed(side, channel, t):
    times = MOTION[side].get('times') or MOTION['times']
    values = MOTION[side][channel]
    if MOTION.get('interpolation') == 'continuous_hermite':
        if t <= times[0]:
            return Vector(values[0])
        if t >= times[-1]:
            return Vector(values[-1])
        for i in range(len(times) - 1):
            if t <= times[i + 1]:
                span = times[i + 1] - times[i]
                u = (t - times[i]) / span
                a, b = Vector(values[i]), Vector(values[i + 1])
                m0, m1 = FLOW_TANGENTS[(side, channel)][i:i + 2]
                return ((2*u**3 - 3*u**2 + 1)*a + (u**3 - 2*u**2 + u)*span*m0
                        + (-2*u**3 + 3*u**2)*b + (u**3 - u**2)*span*m1)
    for i in range(len(times) - 1):
        if t <= times[i + 1]:
            u = max(0., min(1., (t - times[i]) / (times[i + 1] - times[i])))
            kind = MOTION['ease'][i]
            if kind == 'accel':
                u *= u
            elif kind == 'decel':
                u = 1. - (1. - u) ** 2
            elif kind == 'smooth':
                u = u * u * u * (u * (6. * u - 15.) + 10.)
            return Vector(values[i]).lerp(Vector(values[i + 1]), u)
    return Vector(values[-1])


def keyed(side, channel, t):
    # Mirror trajectories onto each anatomical hand, never the gun or mesh.
    role = 'r' if side == LEAD else 'l'
    value = source_keyed(role, channel, t)
    if LEAD == 'l':
        value.y = -value.y
        if channel == 'angles':
            value.z = -value.z
    return value


def envelope(keys, t):
    for (ta, a), (tb, b) in zip(keys, keys[1:]):
        if t <= tb:
            u = max(0., min(1., (t-ta)/(tb-ta)))
            return a+(b-a)*u*u*(3.-2.*u)
    return keys[-1][1]


def open_recovery_fingers(p, idle, side, amount, names, parents, local_rest):
    """Keep the curled index as the pivot; open the other chains for clearance."""
    for finger in ('thumb', 'middle', 'ring', 'pinky'):
        for joint in (1, 2, 3):
            n = f'{finger}_{joint:02d}_{side}'
            if n not in p:
                continue
            parent = parents[n]
            loc, q, scale = (idle[parent].inverted() @ idle[n]).decompose()
            # A partially relaxed anatomical rest pose, not an arbitrary common
            # Euler-axis curl (left and right local joint axes differ).
            weight = (.38 if finger == 'thumb' else .48 if joint == 1 else .88)*amount
            q = q.slerp(local_rest[n].to_quaternion(), weight)
            p[n] = p[parent] @ Matrix.LocRotScale(loc, q, scale)


def flow_tangents(times, values):
    """Shared velocity at every key, without overshooting the authored arc.

    Each coordinate turns only at its own extremum; staggered peaks keep the
    full arm moving around the apex. Only departure and final rest are stopped.
    """
    slopes = [(Vector(b)-Vector(a))/(tb-ta)
              for ta, tb, a, b in zip(times, times[1:], values, values[1:])]
    result = [Vector((0., 0., 0.))]
    for i in range(1, len(times)-1):
        before, after = times[i]-times[i-1], times[i+1]-times[i]
        w1, w2 = 2*after+before, after+2*before
        tangent = Vector((0., 0., 0.))
        for axis in range(3):
            left, right = slopes[i-1][axis], slopes[i][axis]
            if left*right > 0:
                tangent[axis] = (w1+w2)/(w1/left+w2/right)
        result.append(tangent)
    return result + [Vector((0., 0., 0.))]


FLOW_TANGENTS = {}
if MOTION.get('interpolation') == 'continuous_hermite':
    for side in ('r', 'l'):
        times = MOTION[side].get('times') or MOTION['times']
        for channel in ('position', 'angles', 'shoulder', 'elbow'):
            FLOW_TANGENTS[(side, channel)] = flow_tangents(times, MOTION[side][channel])


def solve_arm(p, idle, side, hand, shoulder, pole_target, names):
    """Fixed bone lengths, fixed gun/palm/fingers, full forearm/helper support."""
    upper, lower, wrist = 'upperarm_' + side, 'lowerarm_' + side, 'hand_' + side
    old_s, old_e, old_h = (idle[n].translation for n in (upper, lower, wrist))
    target = hand.translation
    length_u, length_l = (old_e - old_s).length, (old_h - old_e).length
    axis = (target - shoulder).normalized()
    distance = (target - shoulder).length
    reach = (length_u + length_l) * .985
    if distance > reach:
        shoulder = shoulder + axis * (distance - reach)
        distance = reach
    distance = max(abs(length_u - length_l) + .0001, distance)
    pole = pole_target - shoulder
    pole -= axis * pole.dot(axis)
    pole.normalize()
    along = (length_u ** 2 - length_l ** 2 + distance ** 2) / (2. * distance)
    elbow = shoulder + axis * along + pole * math.sqrt(max(0., length_u ** 2 - along ** 2))
    old_normal = (old_e - old_s).cross(old_h - old_e).normalized()
    normal = (elbow - shoulder).cross(target - elbow).normalized()
    swing = (old_e - old_s).rotation_difference(elbow - shoulder)
    hinge = (swing @ old_normal).rotation_difference(normal)
    p[upper] = Matrix.LocRotScale(shoulder, hinge @ swing @ idle[upper].to_quaternion(), idle[upper].to_scale())
    # Carry the idle forearm's roll with the hand, then align its segment. This
    # reproduces the exact idle at zero motion and does not reset to bind roll.
    hand_rotation = hand.to_quaternion() @ idle[wrist].to_quaternion().inverted()
    lower_swing = (hand_rotation @ (old_h - old_e)).rotation_difference(target - elbow)
    p[lower] = Matrix.LocRotScale(elbow, lower_swing @ hand_rotation @ idle[lower].to_quaternion(), idle[lower].to_scale())
    p['clavicle_' + side] = idle['clavicle_' + side].copy()
    p['clavicle_' + side].translation += shoulder - old_s
    delta = hand @ idle[wrist].inverted()
    for n in names:
        if n == wrist or (n.endswith('_' + side) and n.startswith(('thumb', 'index', 'middle', 'ring', 'pinky'))):
            p[n] = delta @ idle[n]
        elif n.endswith('_' + side) and n.startswith(('upperarm_twist', 'lowerarm_twist')):
            segment = upper if n.startswith('upperarm') else lower
            p[n] = p[segment] @ idle[segment].inverted() @ idle[n]
    if 'ik_hand_' + side in p:
        p['ik_hand_' + side] = hand.copy()


receipt = {'weapon': WEAPON, 'revision': REVISION or 'V1', 'duration': MOTION['duration'], 'contact': MOTION['contact'],
           'sample_rate': MOTION['sample_rate'], 'loop': False, 'sides': {},
           'testing': 'Not performed; user testing'}
for side in ('r', 'l'):
    source = SOURCE / WEAPON / side / f'{WEAPON}_{side}_Dual_Editable.blend'
    bpy.context.preferences.filepaths.save_version = 0
    try:
        bpy.ops.wm.open_mainfile(filepath=str(source))
    except RuntimeError as error:
        if 'Missing library override hierarchy root data' not in str(error):
            raise
    scene = bpy.context.scene
    scene.render.fps = 60
    rig = bpy.data.objects[RIG_NAME]
    rig.data.pose_position = 'POSE'
    rig.animation_data_create()
    names = [b.name for b in rig.data.bones]
    parents = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    local_rest = {n: rest[parents[n]].inverted() @ rest[n] if parents[n] else rest[n] for n in names}
    destination = OUT / WEAPON / side
    (destination / 'Animations').mkdir(parents=True, exist_ok=True)
    clips = {}
    actions = {}
    for LEAD, empty in [(lead, empty) for lead in ('r', 'l')
                        for empty in ([False, True] if WEAPON == 'M1911' else [False])]:
        suffix = '_empty' if empty else ''
        idle_name = f'Dual_{WEAPON}_{side}_idle{suffix}'
        idle_action = bpy.data.actions[idle_name]
        rig.animation_data.action = idle_action
        rig.animation_data.action_slot = idle_action.slots[0]
        scene.frame_set(0)
        bpy.context.view_layer.update()
        idle = {b.name: b.matrix.copy() for b in rig.pose.bones}
        grip = idle['WPN_root'].inverted() @ idle['hand_' + side]
        gun_local = {n: idle['WPN_root'].inverted() @ idle[n] for n in names if n.startswith('WPN_')}
        rows, frames, previous = [], [], {}
        count = round(MOTION['duration'] * MOTION['sample_rate'])
        for index in range(count + 1):
            t = index / MOTION['sample_rate']
            p = {n: m.copy() for n, m in idle.items()}
            pivot = idle['hand_' + side].translation
            transform = (Matrix.Translation(pivot + camera(keyed(side, 'position', t)))
                         @ turn(keyed(side, 'angles', t)).to_matrix().to_4x4()
                         @ Matrix.Translation(-pivot))
            root = transform @ idle['WPN_root']
            hand = root @ grip
            opening = 0.
            if side == LEAD:
                opening = envelope(MOTION['finger_open'], t)
                spin = envelope(MOTION['gun_spin'], t)
                # The trigger finger remains attached while the gun turns in
                # its own sagittal plane. No whole-arm 360-degree wrist twist.
                pivot_finger = transform @ idle['index_02_' + side].translation
                axis = transform.to_quaternion() @ camera((0., 1., 0.))
                angle = math.radians(spin)
                root = (Matrix.Translation(pivot_finger)
                        @ Quaternion(axis, angle).to_matrix().to_4x4()
                        @ Matrix.Translation(-pivot_finger) @ root)
            for n, local in gun_local.items():
                p[n] = root @ local
            if index not in (0, count):
                solve_arm(p, idle, side, hand,
                          idle['upperarm_' + side].translation + camera(keyed(side, 'shoulder', t)),
                          idle['lowerarm_' + side].translation + camera(keyed(side, 'elbow', t)), names)
                if opening:
                    open_recovery_fingers(p, idle, side, opening, names, parents, local_rest)
            row = {}
            for n in names:
                local = p[parents[n]].inverted() @ p[n] if parents[n] else p[n]
                loc, q, scale = (local_rest[n].inverted() @ local).decompose()
                if n in previous and previous[n].dot(q) < 0:
                    q.negate()
                previous[n] = q.copy()
                row[n] = (loc, q, scale)
            rows.append(row)
            frames.append(t * scene.render.fps)
        kind = 'quickcombat' + ('_left' if LEAD == 'l' else '') + suffix
        action = bpy.data.actions.new(f'Dual_{WEAPON}_{side}_{kind}')
        action.use_fake_user = True
        rig.animation_data.action = action
        for n in names:
            bone = rig.pose.bones[n]
            bone.rotation_mode = 'QUATERNION'
            for prop in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(prop, frame=0)
        curves = {(c.data_path, c.array_index): c for c in action.layers[0].strips[0].channelbag(action.slots[0]).fcurves}
        for n in names:
            for prop, field, size in [('location', 0, 3), ('rotation_quaternion', 1, 4), ('scale', 2, 3)]:
                for axis in range(size):
                    curve = curves[(f'pose.bones["{n}"].{prop}', axis)]
                    curve.keyframe_points.clear()
                    curve.keyframe_points.add(len(frames))
                    curve.keyframe_points.foreach_set('co', [v for frame, row in zip(frames, rows) for v in (frame, row[n][field][axis])])
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'
                    curve.update()
        rig.animation_data.action_slot = action.slots[0]
        scene.frame_start, scene.frame_end = 0, round(MOTION['duration'] * scene.render.fps)
        scene.frame_set(0)
        bpy.ops.object.select_all(action='DESELECT')
        rig.hide_set(False)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        fbx = destination / 'Animations' / f'A_Dual_{WEAPON}_{side}_{kind}.fbx'
        bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'ARMATURE'},
                                axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
                                bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                                bake_anim_step=.5, bake_anim_simplify_factor=0)
        clips[kind] = {'fbx': str(fbx), 'idle': idle_name, 'striking_hand': LEAD}
        actions[kind] = action
        print('DUAL_QUICKCOMBAT_EXPORTED', WEAPON, side, kind, flush=True)
    rig.animation_data.action = actions['quickcombat']
    rig.animation_data.action_slot = actions['quickcombat'].slots[0]
    scene.frame_set(0)
    blend = destination / f'{WEAPON}_{side}_QuickCombat_Editable.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    receipt['sides'][side] = {'source': str(source), 'blend': str(blend), 'clips': clips}
(OUT / f'{WEAPON}-authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('DUAL_QUICKCOMBAT_AUTHOR_COMPLETE', WEAPON, flush=True)
