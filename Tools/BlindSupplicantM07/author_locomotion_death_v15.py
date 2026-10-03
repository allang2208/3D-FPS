"""M07 V15 whole-body gait and grounded loss-of-strength death.

Only three animation actions are authored. The V13 display meshes, UVs,
weights, object unit transforms and the 83-bone V11 reference are retained.
Source diagnosis is restricted to the movement/death problems requested by
the user. No UE, runtime tests, renders or screenshots are launched.
"""
from pathlib import Path
import copy
import json
import math
import sys

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'MotionRecoveryV15/LocomotionDeath'
MASTER = ROOT/'CombatMagicV14/Motion/M07_Original_SweepCasting_V14.blend'
FPS = 30
UP, RIGHT, FORWARD = Vector((0, 0, 1)), Vector((1, 0, 0)), Vector((0, -1, 0))
sys.path.insert(0, str(Path(__file__).parent))
import author_motion_v04 as motion
import author_running_v12 as running


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def rot(axis, degrees):
    return Quaternion(axis, math.radians(degrees))


def angle(q):
    return math.degrees(2*math.acos(min(1, abs(q.normalized().w))))


def smooth(t, a=0., b=1.):
    x = min(1., max(0., (t-a)/max(.0001, b-a)))
    return x*x*(3-2*x)


def rampkeys(t, keys):
    if t <= keys[0][0]:
        return keys[0][1]
    for (a, x), (b, y) in zip(keys, keys[1:]):
        if t <= b:
            return x+(y-x)*smooth(t, a, b)
    return keys[-1][1]


def cache_action(rig, action, count, ordered):
    motion.activate(rig, action)
    frames = []
    for i in range(count):
        bpy.context.scene.frame_set(i+1)
        bpy.context.view_layer.update()
        frames.append({p.name: p.matrix.copy() for p in ordered})
    return frames


def source_diagnosis(rest, cache):
    result = {'source': str(MASTER), 'scope': 'Requested gait and death source-data diagnosis; no game testing',
              'reference_points_cm': {n: list(rest[n].translation) for n in
                  ('pelvis', 'spine_05', 'head', 'thigh_l', 'calf_l', 'foot_l', 'ball_l', 'hand_l')},
              'clips': {}}
    for role, frames in cache.items():
        first = frames[0]
        r = {'pelvis_xyz_min_cm': [min(f['pelvis'].translation[k] for f in frames) for k in range(3)],
             'pelvis_xyz_max_cm': [max(f['pelvis'].translation[k] for f in frames) for k in range(3)],
             'relative_joint_rotation_degrees': {}}
        for n in ('pelvis', 'spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05',
                  'clavicle_l', 'clavicle_r', 'head'):
            r['relative_joint_rotation_degrees'][n] = max(angle(f[n].to_quaternion()@first[n].to_quaternion().inverted()) for f in frames)
        r['local_articulation_span_degrees'] = {}
        for n in ('spine_02', 'spine_03', 'spine_04', 'spine_05', 'clavicle_l', 'clavicle_r'):
            parent = bpy.data.objects['M07_Original_Armature'].data.bones[n].parent.name if bpy.data.objects.get('M07_Original_Armature') else next(o for o in bpy.data.objects if o.type == 'ARMATURE').data.bones[n].parent.name
            opening = first[parent].to_quaternion().inverted()@first[n].to_quaternion()
            r['local_articulation_span_degrees'][n] = max(angle((f[parent].to_quaternion().inverted()@f[n].to_quaternion())@opening.inverted()) for f in frames)
        if role == 'Death':
            r['handoff_seconds'] = 1.44
            f = frames[round(1.44*FPS)]
            r['handoff_joint_xyz_cm'] = {n: list(f[n].translation) for n in
                ('pelvis', 'head', 'calf_l', 'calf_r', 'hand_l', 'hand_r', 'foot_l', 'foot_r')}
            r['whole_clip_lowest_joint_z_cm'] = min(m.translation.z for frame in frames for m in frame.values())
        result['clips'][role] = r
    return result


def body_support_source(rig):
    """Original visible BODY only; gill/cloth geometry does not drive feet."""
    obj = bpy.data.objects['M07_OriginalBody_Display']
    xyz = np.empty(len(obj.data.vertices)*3, dtype=np.float64)
    obj.data.vertices.foreach_get('co', xyz)
    xyz = xyz.reshape((-1, 3))
    points = np.column_stack((xyz, np.ones(len(xyz))))
    points = points@np.array(rig.matrix_world.inverted()@obj.matrix_world, dtype=float).T
    names = {g.index: g.name for g in obj.vertex_groups}
    groups = {n: [[], []] for n in rig.data.bones.keys()}
    regions = []
    for i, v in enumerate(obj.data.vertices):
        useful = [(names[g.group], g.weight) for g in v.groups if names[g.group] in groups and g.weight > 0.]
        dominant = max(useful, key=lambda x: x[1])[0] if useful else 'pelvis'
        if dominant.startswith(('foot_', 'ball_')):
            region = 'foot_'+dominant[-1]
        elif dominant.startswith(('thigh_', 'calf_')):
            region = 'leg_'+dominant[-1]
        elif dominant.startswith(('upperarm_', 'lowerarm_', 'hand_', 'thumb_', 'index_', 'middle_', 'ring_', 'pinky_')):
            region = 'arm_'+dominant[-1]
        else:
            region = 'body'
        regions.append(region)
        total = sum(w for _, w in useful)
        for n, w in useful:
            groups[n][0].append(i)
            groups[n][1].append(w/max(.00001, total))
    return points, {n: (np.array(indices, dtype=int), np.array(weights, dtype=float)) for n, (indices, weights) in groups.items() if indices}, np.array(regions)


def sampled_body_floor(rig, rest, support, count):
    points, groups, regions = support
    rows = []
    for i in range(count):
        bpy.context.scene.frame_set(i+1)
        bpy.context.view_layer.update()
        z = np.zeros(len(points), dtype=float)
        for n, (indices, weights) in groups.items():
            transform = np.array(rig.pose.bones[n].matrix@rest[n].inverted(), dtype=float)
            z[indices] += (points[indices]@transform[2])*weights
        rows.append({'seconds': i/FPS, 'body_min_z_cm': float(z.min()),
                     'lowest_vertex_index': int(np.argmin(z)),
                     'lowest_rest_xyz_cm': list(points[np.argmin(z), :3]),
                     'torso_lowest_vertex_index': int(np.flatnonzero(regions == 'body')[np.argmin(z[regions == 'body'])]),
                     'region_min_z_cm': {r: float(z[regions == r].min()) for r in set(regions)}})
    return {'source_scope': 'Requested original display-body deformation/floor diagnosis, excluding cloth and hidden high/proxy objects',
            'floor_z_cm': 0., 'samples': rows,
            'pre_handoff_min_z_cm': min(row['body_min_z_cm'] for row in rows if row['seconds'] <= 1.44),
            'pre_handoff_region_min_z_cm': {r: min(row['region_min_z_cm'][r] for row in rows if row['seconds'] <= 1.44) for r in set(regions)}}


def put(target, n, position, q):
    target[n] = Matrix.LocRotScale(position, q, Vector((1, 1, 1)))


def inherited(target, rest, local, pose):
    n, parent = pose.name, pose.parent.name if pose.parent else None
    if parent:
        position = target[parent]@local[n].translation
        delta = target[parent].to_quaternion()@rest[parent].to_quaternion().inverted()
        q = delta@rest[n].to_quaternion()
    else:
        position, q = rest[n].translation.copy(), rest[n].to_quaternion()
    return position, q


def leg_solution(rest, hip, ankle, delta, side, pole_override=None, knee_floor=None, minimal_world=False):
    thigh, calf, foot = ('thigh_'+side, 'calf_'+side, 'foot_'+side)
    original_u = rest[calf].translation-rest[thigh].translation
    original_l = rest[foot].translation-rest[calf].translation
    l1, l2 = original_u.length, original_l.length
    v = ankle-hip
    distance = min(v.length, (l1+l2)*.997)
    distance = max(abs(l1-l2)+2., distance)
    axis = v.normalized()
    pole = pole_override.copy() if pole_override is not None else delta@FORWARD
    pole -= axis*pole.dot(axis)
    if pole.length < .001:
        pole = delta@RIGHT
        pole -= axis*pole.dot(axis)
    pole.normalize()
    along = (l1*l1-l2*l2+distance*distance)/(2*distance)
    height = math.sqrt(max(0., l1*l1-along*along))
    base = hip+axis*along
    if knee_floor is not None and base.z+pole.z*height < knee_floor:
        upward = UP-axis*UP.dot(axis)
        upward.normalize()
        # The knee-circle's upper arc is selected before floor contact;
        # keeping a forward-only pole while the pelvis tips was the reason
        # a right knee could rotate under the floor in the first draft.
        if base.z+upward.z*height >= knee_floor:
            lo, hi = 0., 1.
            for _ in range(14):
                mid = (lo+hi)*.5
                candidate = pole.lerp(upward, mid).normalized()
                if base.z+candidate.z*height < knee_floor:
                    lo = mid
                else:
                    hi = mid
            pole = pole.lerp(upward, hi).normalized()
        else:
            pole = upward
    knee = base+pole*height
    ankle = hip+axis*distance
    u, l = (knee-hip).normalized(), (ankle-knee).normalized()
    # Original orientation is transported by the pelvis and the smallest
    # possible segment swing. No forced hinge-frame axial rotation.
    if minimal_world:
        du = original_u.normalized().rotation_difference(u)
        dl = original_l.normalized().rotation_difference(l)
    else:
        du = (delta@original_u.normalized()).rotation_difference(u)@delta
        dl = (du@original_l.normalized()).rotation_difference(l)@du
    return knee, ankle, du, dl


def install_legs(target, rest, local, ordered, feet, death=False):
    pelvis_delta = target['pelvis'].to_quaternion()@rest['pelvis'].to_quaternion().inverted()
    for side in ('l', 'r'):
        hip = target['thigh_'+side].translation.copy()
        goal, foot_q, ball_q = feet[side]
        knee, ankle, du, dl = leg_solution(rest, hip, goal, pelvis_delta, side,
            pole_override=FORWARD if death else None,
            knee_floor=22. if death else None, minimal_world=False)
        put(target, 'thigh_'+side, hip, du@rest['thigh_'+side].to_quaternion())
        put(target, 'calf_'+side, knee, dl@rest['calf_'+side].to_quaternion())
        put(target, 'foot_'+side, ankle, foot_q)
        put(target, 'ball_'+side, target['foot_'+side]@local['ball_'+side].translation, ball_q)


def arm_directions(rest, torso, phase, role, side, death_t=None, shoulder=None):
    sign = 1 if side == 'l' else -1
    upper_name, lower_name, hand_name = ('upperarm_'+side, 'lowerarm_'+side, 'hand_'+side)
    original_u = (rest[lower_name].translation-rest[upper_name].translation).normalized()
    original_l = (rest[hand_name].translation-rest[lower_name].translation).normalized()
    if death_t is None:
        wave = -math.cos(2*math.pi*phase-.10)
        swing = (5+34*wave) if role == 'SlowWalk' else (8+45*wave)
        elbow = (43+12*(.5+.5*wave)) if role == 'SlowWalk' else (77+17*(.5+.5*wave))
        abduction = 13 if role == 'SlowWalk' else 15
        desired = Vector((sign*math.sin(math.radians(abduction)), -math.sin(math.radians(swing)), -math.cos(math.radians(swing))))
        upper = torso@desired.normalized()
        flex = torso@FORWARD
        flex -= upper*flex.dot(upper)
        flex.normalize()
        lower = (upper*math.cos(math.radians(elbow))+flex*math.sin(math.radians(elbow))).normalized()
    else:
        t = death_t
        brace = smooth(t, .55, 1.32)*(1-smooth(t, 1.7, 2.15))
        relax = smooth(t, 1.35, 2.35)
        l1 = (rest[lower_name].translation-rest[upper_name].translation).length
        l2 = (rest[hand_name].translation-rest[lower_name].translation).length
        if side == 'r':
            # The supporting palm never inherits a downward torso roll as
            # an unrestricted arm swing. Its actual floor contact is a goal
            # for the complete shoulder/elbow chain.
            relative = Vector((-.20-.35*brace, -.20, -.92+.24*brace)).normalized()*(l1+l2)*.86
            wrist = shoulder+torso@relative
            wrist.z = max(wrist.z, 67.-14.*relax)
        else:
            relative = Vector((.24, -.24-.20*brace, -.92+.15*brace)).normalized()*(l1+l2)*.86
            wrist = shoulder+torso@relative
            wrist.z = max(wrist.z, 60.-8.*relax)
        v = wrist-shoulder
        distance = max(abs(l1-l2)+2., min(v.length, (l1+l2)*.955))
        axis = v.normalized()
        pole = torso@Vector((sign*.28, -.65, -.6))
        pole -= axis*pole.dot(axis)
        pole.normalize()
        along = (l1*l1-l2*l2+distance*distance)/(2*distance)
        elbow = axis*along+pole*math.sqrt(max(0., l1*l1-along*along))
        upper, lower = elbow.normalized(), (axis*distance-elbow).normalized()
    du = (torso@original_u).rotation_difference(upper)@torso
    dl = (du@original_l).rotation_difference(lower)@du
    return du, dl


def install_arms(target, rest, local, ordered, phase, role, t=None):
    torso = target['spine_05'].to_quaternion()@rest['spine_05'].to_quaternion().inverted()
    deltas = {}
    for side, offset in (('l', 0.), ('r', .5)):
        deltas[side] = arm_directions(rest, torso, (phase+offset)%1., role, side, t, target['upperarm_'+side].translation)
    for pose in ordered:
        n = pose.name
        if not n.startswith(('upperarm_', 'lowerarm_', 'hand_', 'thumb_', 'index_', 'middle_', 'ring_', 'pinky_', 'gill_')):
            continue
        parent = pose.parent.name
        position, q = inherited(target, rest, local, pose)
        if n.startswith('upperarm_'):
            q = deltas[n[-1]][0]@rest[n].to_quaternion()
        elif n.startswith('lowerarm_'):
            q = deltas[n[-1]][1]@rest[n].to_quaternion()
        elif n.startswith('hand_'):
            side = n[-1]
            q = deltas[side][1]@rest[n].to_quaternion()
            hand_delta = deltas[side][1]
            q = rot(hand_delta@RIGHT, 2.5*math.sin(2*math.pi*(phase+(0 if side == 'l' else .5))))@q
        elif n.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')) and '_metacarpal_' not in n:
            side, digit, segment = n[-1], n.split('_')[0], int(n.split('_')[1])
            hand = 'hand_'+side
            along = (rest['middle_01_'+side].translation-rest[hand].translation).normalized()
            across = (rest['index_01_'+side].translation-rest['pinky_01_'+side].translation).normalized()
            normal = (target[hand].to_quaternion()@rest[hand].to_quaternion().inverted())@along.cross(across).normalized()
            direction = q@Vector((0, 1, 0))
            axis = direction.cross(normal)
            if axis.length > .0001:
                degrees = (11, 17, 12)[segment-1] if digit != 'thumb' else (8, 10, 8)[segment-1]
                if t is not None:
                    degrees *= 1-.65*smooth(t, .5, 2.2)
                else:
                    degrees += 1.8*math.sin(2*math.pi*phase+.22*segment)
                q = rot(axis.normalized(), degrees)@q
        elif n.startswith('gill_'):
            _, panel, segment = n.split('_')
            stagger = -(int(panel)-1)*.38
            breath = math.sin(2*math.pi*phase+stagger)-math.sin(stagger)
            if t is not None:
                breath *= 1-smooth(t, .2, 1.5)
            q = rot(target[parent].to_quaternion()@RIGHT, (.7+.55*int(segment))*breath)@q
        put(target, n, position, q)


def move_target(rest, local, ordered, old, u, role):
    theta = 2*math.pi*u
    run = role == 'Chase'
    hip_yaw = (10 if run else 7)*math.cos(theta)
    hip_roll = (4.5 if run else 3.2)*math.sin(theta-.18)
    lean = 3.5 if run else 1.8
    p = old['pelvis'].translation.copy()
    p.x += (3.8 if run else 4.8)*math.sin(theta-.15)
    p.y += (2.0 if run else 1.4)*math.sin(2*theta+.28)
    p.z += (3.0 if run else 1.8)*(-math.cos(2*theta+.12))
    pelvis_delta = rot(RIGHT, lean)@rot(UP, -hip_yaw)@rot(FORWARD, hip_roll)
    target = {}
    for pose in ordered:
        n = pose.name
        position, q = inherited(target, rest, local, pose)
        if n == 'pelvis':
            position, q = p, pelvis_delta@rest[n].to_quaternion()
        elif n.startswith('spine_'):
            part = int(n.split('_')[1])
            yaw = hip_yaw*(.32 if part < 3 else .43)
            pitch = (2.0 if run else 1.0)+(.95 if run else .55)*math.sin(2*theta+.18*part)
            roll = -hip_roll*.17
            q = rot(UP, yaw)@rot(RIGHT, pitch)@rot(FORWARD, roll)@q
        elif n.startswith('clavicle_'):
            sign = 1 if n.endswith('_l') else -1
            q = rot(UP, sign*(2.2 if run else 1.4)*math.sin(theta))@rot(FORWARD, sign*(2.7 if run else 1.6)*math.cos(theta-.12))@q
        elif n.startswith(('neck_', 'head')):
            # Counterrotation is shared over three joints, not a rigid fixed
            # head. Small pitch lag retains the low-headed identity.
            q = rot(UP, -hip_yaw*.26)@rot(FORWARD, -hip_roll*.06)@rot(RIGHT, -.9 if run else -.5)@q
        put(target, n, position, q)
    # Keep the V13 support/recovery target points and phase, while solving
    # their fixed-length legs from the newly mobile pelvis.
    feet = {s: (old['foot_'+s].translation.copy(), old['foot_'+s].to_quaternion(), old['ball_'+s].to_quaternion()) for s in ('l', 'r')}
    settle = 0.
    for side, (ankle, _, _) in feet.items():
        hip = target['thigh_'+side].translation
        total = (rest['calf_'+side].translation-rest['thigh_'+side].translation).length+(rest['foot_'+side].translation-rest['calf_'+side].translation).length
        horizontal = (hip.x-ankle.x)**2+(hip.y-ankle.y)**2
        max_z = math.sqrt(max(0., (total*.994)**2-horizontal))
        settle = max(settle, hip.z-ankle.z-max_z)
    if settle > 0:
        for m in target.values():
            m.translation.z -= settle
    install_legs(target, rest, local, ordered, feet)
    install_arms(target, rest, local, ordered, u, role)
    return target


def death_target(rest, local, ordered, t):
    # A world-fixed container/reference root never moves below the floor.
    # The pelvis follows support collapse, then a right-side fall: distinct
    # stages replace the old donor pelvis displacement/leg-length scaling.
    collapse = smooth(t, .18, 1.05)
    fall = smooth(t, .80, 1.95)
    settle = smooth(t, 1.80, 2.35)
    # M07's real body shell retains a wide lower back-organ envelope. A
    # pure ninety-degree lateral roll would push that original skin through
    # the floor. The fall is therefore diagonal/right-forward, with chest
    # flexion carrying the body toward a supported half-prone resting pose.
    side_angle = rampkeys(t, [(0, 0), (.32, 1), (.85, 6), (1.44, 23), (1.90, 27), (2.4, 25)])
    forward_angle = rampkeys(t, [(0, 0), (.22, 9), (.78, 22), (1.44, 50), (1.90, 70), (2.4, 74)])
    p = rest['pelvis'].translation.copy()
    p.x -= 16*collapse+42*fall
    p.y -= 8*collapse+5*fall
    # Floor-relative hip height is an anatomical body support choice, not a
    # minimum-vertex lift applied indiscriminately to all model/cloth parts.
    end_height = 40.
    p.z = rampkeys(t, [(0, rest['pelvis'].translation.z), (.32, rest['pelvis'].translation.z-8.),
        (.85, 108.), (1.44, 94.), (1.82, 84.), (2.12, 54.), (2.35, end_height), (2.4, end_height)])
    p.z += 1.5*settle
    delta = rot(FORWARD, side_angle)@rot(RIGHT, forward_angle)@rot(UP, -5*collapse)
    target = {}
    for pose in ordered:
        n = pose.name
        position, q = inherited(target, rest, local, pose)
        if n == 'pelvis':
            position, q = p, delta@rest[n].to_quaternion()
        elif n.startswith('spine_'):
            part = int(n.split('_')[1])
            pitch = (1.5+part*.25)*collapse*(1-.65*fall)
            q = rot(delta@FORWARD, -3.6*fall)@rot(delta@RIGHT, pitch)@rot(delta@UP, -.9*collapse)@q
        elif n.startswith(('neck_', 'head')):
            q = rot(delta@RIGHT, 2.2*collapse+1.6*fall)@q
        put(target, n, position, q)
    feet = {}
    for side, sign in (('l', 1), ('r', -1)):
        old = rest['foot_'+side].translation.copy()
        release = smooth(t, 1.00 if side == 'l' else 1.08, 1.88)
        rest_offset = old-rest['pelvis'].translation
        lying = p+delta@(rest_offset*.53)
        lying.z = 13.+(5. if side == 'l' else 0.)
        goal = old.lerp(lying, release)
        goal.z = max(goal.z, old.z+18.*release+7.*collapse)
        # Stance feet flex during collapse, then turn into the side-lying
        # recovery. L/R differences avoid a synchronized folding silhouette.
        # A falling torso must not pitch the long toes vertically into the
        # ground. Feet keep their own support frame and only roll sideways
        # after releasing stance.
        foot_delta = rot(FORWARD, side_angle*release)
        foot_q = foot_delta@rot(RIGHT, -8*collapse*(1-release))@rest['foot_'+side].to_quaternion()
        ball_q = foot_delta@rest['ball_'+side].to_quaternion()
        feet[side] = goal, foot_q, ball_q
    install_legs(target, rest, local, ordered, feet, True)
    install_arms(target, rest, local, ordered, t/4., 'Death', t)
    return target


def export(rig, action, path, frames):
    motion.activate(rig, action)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, frames
    scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'ARMATURE'},
        add_leaf_bones=False, use_armature_deform_only=False, armature_nodetype='NULL',
        bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True,
        bake_anim_step=1, bake_anim_simplify_factor=0., axis_forward='-Y', axis_up='Z',
        apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.data.bones.get('gill_01_00'))
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    local = {b.name: b.parent.matrix_local.inverted()@b.matrix_local if b.parent else b.matrix_local.copy() for b in rig.data.bones}
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    original = json.loads((ROOT/'RecoveryOriginalV13/motion_manifest_v13.json').read_text(encoding='utf-8'))
    visibility = {o.name: o.hide_viewport for o in bpy.data.objects if o.type == 'MESH'}
    for n in visibility:
        bpy.data.objects[n].hide_viewport = True
    cache = {role: cache_action(rig, bpy.data.actions[original['clips'][role]['action']], original['clips'][role]['frames'], ordered)
             for role in ('SlowWalk', 'Chase', 'Death')}
    diagnosis = source_diagnosis(rest, cache)
    support = body_support_source(rig)
    motion.activate(rig, bpy.data.actions[original['clips']['Death']['action']])
    diagnosis['death_original_display_grounding'] = sampled_body_floor(rig, rest, support, original['clips']['Death']['frames'])
    write(OUT/'source_motion_diagnosis_v15.json', diagnosis)
    print('M07_V15_REQUESTED_SOURCE_DIAGNOSIS '+json.dumps({
        'source': str(MASTER), 'clips': diagnosis['clips'],
        'old_death_before_handoff_skin_floor_cm': diagnosis['death_original_display_grounding']['pre_handoff_min_z_cm']}), flush=True)
    if '--diagnose-only' in sys.argv:
        return
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.
    scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', .01
    manifest = {'revision': 'MotionRecoveryV15LocomotionDeath', 'fps': FPS, 'source_master': str(MASTER),
        'source': str(OUT/'M07_Original_LocomotionDeath_V15.blend'), 'reference_skeleton': original['ue_skeleton'],
        'mesh_geometry_uv_weights_preserved': True, 'reference_pose_modified': False,
        'rig_object_matrix_world': motion.rows(rig.matrix_world), 'bone_reference': {n: motion.rows(m) for n, m in rest.items()},
        'bone_names': list(rest), 'clips': {}, 'source_diagnosis': str(OUT/'source_motion_diagnosis_v15.json'),
        'root_motion': False, 'runtime_tested': False, 'rendered': False, 'visual_accepted': False}
    actions = {}
    for role in ('SlowWalk', 'Chase', 'Death'):
        count = original['clips'][role]['frames']
        duration = (count-1)/FPS
        action = bpy.data.actions.new('A_M07_'+role+'_MotionRecoveryV15')
        action.use_fake_user = True
        motion.activate(rig, action)
        previous = {}
        for i in range(count):
            frame, t, u = i+1, i/FPS, i/(count-1)
            scene.frame_set(frame)
            target = death_target(rest, local, ordered, t) if role == 'Death' else move_target(rest, local, ordered, cache[role][i], u, role)
            running.insert_frame(rig, target, rest, ordered, frame, previous)
        scene.frame_set(0)
        for p in ordered:
            p.matrix_basis = Matrix.Identity(4)
            for channel in ('location', 'rotation_quaternion', 'scale'):
                p.keyframe_insert(data_path=channel, frame=0, group=p.name)
        for curve in running.curves(action):
            for point in curve.keyframe_points:
                point.interpolation = 'LINEAR'
        if role == 'Death':
            grounding = sampled_body_floor(rig, rest, support, count)
            write(OUT/'death_body_grounding_source_v15.json', grounding)
            print('M07_V15_DEATH_SOURCE_BODY_FLOOR '+json.dumps({k: v for k, v in grounding.items() if k != 'samples'}), flush=True)
        file = OUT/('A_M07_'+role+'.fbx')
        export(rig, action, file, count)
        entry = {'role': role, 'action': action.name, 'file': str(file),
            'asset': '/Game/Monsters/BlindSupplicantM07/AnimationsMotionRecoveryV15/A_M07_'+role,
            'fps': FPS, 'frames': count, 'duration': duration, 'seconds': duration,
            'reference_only_blender_frame': 0, 'exported_blender_frame_start': 1,
            'exported_blender_frame_end': count, 'loop': role != 'Death', 'root_motion': False,
            'bone_tracks': list(rest), 'all_child_locations_zero_except_pelvis': True}
        if role == 'Death':
            entry.update(handoff_fraction=.60, handoff_seconds=duration*.60,
                death_ragdoll_seconds=duration*.60, hold_last_pose=True,
                grounding='Original stance anchors until support loss; anatomical knee-circle floor constraint, independent long-toe support frame; diagonal right-forward fall; positive original display-body support envelope before physical handoff; no container-root floor translation',
                source_body_pre_handoff_minimum_cm=grounding['pre_handoff_min_z_cm'],
                source_body_all_clip_minimum_cm=min(row['body_min_z_cm'] for row in grounding['samples']),
                source_grounding_data=str(OUT/'death_body_grounding_source_v15.json'),
                choreography='Loss of strength 0-.32s; asymmetric knee collapse .18-1.05s; diagonal right-forward balance loss .80-1.95s; physical handoff at 1.44s during the fall; fallback settle to half-prone by 2.35s')
        else:
            speed = 360. if role == 'Chase' else 160.
            entry.update(speed_cm_s=speed, expected_speed_cm_s=speed, stride_cm=speed*duration,
                step_cm=speed*duration*.5, stance_fraction=original['clips'][role].get('stance_fraction', .38 if role == 'Chase' else .61),
                support_phase_retained_from='OriginalV13', foot_contact=copy.deepcopy(original['clips'][role].get('foot_contact', {})),
                pelvis_chest_arm_phase='Hip yaw/weight transfer follows support; successive spine joints counterrotate, clavicles follow swing; ipsilateral arm retracts as foot advances; head counterrotates',
                grounding='V13 actual foot/ball target positions, orientations and support phase retained; both legs re-solved with unchanged bone lengths and minimum reference swing',
                child_frame_policy='World-defined anatomical rotations converted using explicit computed parent; no stale dependency-graph matrix setters')
        manifest['clips'][role], actions[role] = entry, action
        print('M07_V15_LOCOMOTION_DEATH_EXPORTED '+role+' '+str(file), flush=True)
    authored_cache = {role: cache_action(rig, actions[role], entry['frames'], ordered) for role, entry in manifest['clips'].items()}
    notes = source_diagnosis(rest, authored_cache)
    notes.update(source=str(OUT/'M07_Original_LocomotionDeath_V15.blend'),
        reason='Old Death already deformed the actual original display body under its floor before the 60% physical handoff; source pelvis reached 4.89cm and torso reached almost 180deg, with handoff right ankle -8.04cm. Old locomotion had global torso rotation but spine_05 local motion below 1deg, insufficient weight-transfer/segment differentiation. New actions couple hip/chest/clavicles/arms rather than rotate one torso slab.',
        preservation='Only three new action datablocks and metadata; original V13 mesh, UV, weights, object transform and V11 reference retained; V14 sweep/cast and other source actions retained unchanged',
        death_body_grounding=str(OUT/'death_body_grounding_source_v15.json'),
        runtime_tested=False, rendered=False)
    write(OUT/'authored_motion_notes_v15.json', notes)
    manifest['authored_motion_notes'] = str(OUT/'authored_motion_notes_v15.json')
    for n, hidden in visibility.items():
        bpy.data.objects[n].hide_viewport = hidden
    motion.activate(rig, actions['Chase'])
    scene.frame_start, scene.frame_end = 1, manifest['clips']['Chase']['frames']
    scene.frame_set(0)
    rig['locomotion_death_revision'] = 'V15 whole-body coupled gait and anatomically grounded loss-of-strength death; unchanged V13 mesh/V11 bind'
    bpy.ops.wm.save_as_mainfile(filepath=manifest['source'], compress=True)
    manifest.update(source_saved=True, animation_fbx_exported=True, ue_imported=False)
    write(OUT/'motion_manifest_v15.json', manifest)
    print('M07_V15_LOCOMOTION_DEATH_MASTER_SAVED '+manifest['source'], flush=True)


if __name__ == '__main__':
    main()
