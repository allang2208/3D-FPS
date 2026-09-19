"""Adapt the user-liked V36 hand choreography to front idle and outside carry.

Authoring and FBX export only. No playback, render or acceptance is performed.
The V36 contact transforms and finger keys are inputs, never regenerated here.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

P = Path(__file__).parent
V36 = P.parent / 'ReferenceReplicaV36'
plan = json.loads((P / 'motion_plan.json').read_text(encoding='utf-8'))
data = json.loads((V36 / 'authoring_inputs.json').read_text())
replica = json.loads((V36 / 'reference_poses.json').read_text())
SOURCE = V36 / 'AzureRunesword_ReferenceReplicaV36.blend'
FPS, DURATION = plan['fps'], plan['duration']
CORE_START, CORE_END = plan['core_start'], plan['core_end']
ONE = Vector((1, 1, 1))
OUT = P / 'Export'
OUT.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
s = bpy.context.scene
r = bpy.data.objects[data['rig']]
rest = {n: Matrix(v['rest']) for n, v in data['bones'].items()}
idle = {n: Matrix(v['idle']) for n, v in data['bones'].items()}
parent = {n: v['parent'] for n, v in data['bones'].items()}
local_rest = {n: rest[parent[n]].inverted() @ m if parent[n] else m for n, m in rest.items()}
local_idle = {n: idle[parent[n]].inverted() @ m if parent[n] else m for n, m in idle.items()}
native = [{'hand': Matrix(v['hand_r']), 'weapon': Matrix(v['weapon']),
           'fingers': {n: Matrix(m) for n, m in v['finger_local'].items()}}
          for v in replica['frames']]
grips = {side: idle['WPN_root'].inverted() @ idle['hand_' + side] for side in ('l', 'r')}
fingers = {side: [n for n in rest if n.endswith('_' + side) and
                 n.startswith(('thumb', 'index', 'middle', 'ring', 'pinky'))] for side in ('l', 'r')}


def depth(n):
    return 1 + depth(parent[n]) if parent[n] else 0


for side in fingers:
    fingers[side].sort(key=depth)


def ease(x):
    x = max(0., min(1., x))
    return max(0., min(1., x*x*x*(x*(6*x - 15) + 10)))


def mix(a, b, w):
    w = max(0., min(1., w))
    return Matrix.LocRotScale(a.translation.lerp(b.translation, w),
                              a.to_quaternion().slerp(b.to_quaternion(), w), ONE)


def native_at(t):
    # Exactly the V36 hand-local interpolation through the 30 fps spin keys.
    f = max(0., min(60., t * 30))
    i = min(59, int(f))
    u = f - i
    a, b = native[i], native[i + 1]
    W = mix(a['weapon'], b['weapon'], u)
    if i >= 9 or (i == 0 and u == 0):
        H = W @ grips['r']
    else:
        H = mix(a['hand'], b['hand'], u)
        relative = mix(a['hand'].inverted() @ a['weapon'],
                       b['hand'].inverted() @ b['weapon'], u)
        W = H @ relative
    fs = {n: mix(a['fingers'][n], b['fingers'][n], u) for n in fingers['r']}
    return H, W, fs


# Rotate and translate the entire hand-and-weapon pair, so the successful
# changing grasp survives. A 65 degree yaw places the backward quadrant beside
# the right shoulder and the downward quadrant ahead of the forearm.
SPIN_ROT = Quaternion(Vector((0, 0, 1)), math.radians(plan['spin_plane_yaw_degrees']))
START_WRIST = Vector(plan['spin_start_wrist'])
core_origin = native_at(0.)[0].translation.copy()
CORE_FRAME = Matrix.LocRotScale(START_WRIST, SPIN_ROT, ONE) @ Matrix.Translation(-core_origin)


def core_at(t):
    H, W, fs = native_at(t)
    return CORE_FRAME @ H, CORE_FRAME @ W, fs


H0, W0, FS0 = core_at(0.)
H9, W9, FS9 = core_at(.3)


def closed_pose(hand_position, weapon_rotation):
    # Turn about the held handle, with the accepted closed contact as a rigid
    # transform. Do not rotate a disconnected sword about its mesh origin.
    W = Matrix.LocRotScale(Vector(hand_position) - weapon_rotation @ grips['r'].translation,
                           weapon_rotation, ONE)
    return W @ grips['r'], W


def blade_direction(q, direction):
    return (q @ Vector((0, 0, 1))).rotation_difference(Vector(direction).normalized()) @ q


BASE_Q = W0.to_quaternion()
CARRY_Q = blade_direction(BASE_Q, plan['shoulder_blade_direction'])
CARRY_H, CARRY_W = closed_pose(plan['shoulder_wrist'], CARRY_Q)
ENTRY_H, ENTRY_W = closed_pose(plan['entry_clear_wrist'], BASE_Q)
EXIT_H, EXIT_W = closed_pose(plan['exit_clear_wrist'], BASE_Q)


def bridge(aH, aW, bH, bW, u, arc=(0., 0., 0.)):
    w = ease(u)
    # A bowed wrist path keeps the shoulder-to-front transitions on the right.
    position = aH.translation.lerp(bH.translation, w) + Vector(arc) * (4*w*(1-w))
    q = aW.to_quaternion().slerp(bW.to_quaternion(), w)
    return closed_pose(position, q)


def right_at(t):
    if t < .18:
        return idle['hand_r'].copy(), idle['WPN_root'].copy(), local_idle
    if t < .45:
        H, W = bridge(idle['hand_r'], idle['WPN_root'], ENTRY_H, ENTRY_W,
                      (t - .18) / .27, (.018, .020, .012))
    elif t < .73:
        H, W = bridge(ENTRY_H, ENTRY_W, CARRY_H, CARRY_W,
                      (t - .45) / .28, (.018, 0., .025))
    elif t < CORE_START:
        H, W = bridge(CARRY_H, CARRY_W, H0, W0,
                      (t - .73) / (CORE_START - .73), (.018, .015, .025))
    elif t <= CORE_END:
        return core_at(t - CORE_START)
    elif t < 1.64:
        H, W = bridge(H9, W9, CARRY_H, CARRY_W,
                      (t - CORE_END) / (1.64 - CORE_END), (.020, .018, .026))
    elif t < 1.85:
        # A small continuation avoids a frozen two-second presentation pose.
        u = ease((t - 1.64) / .21)
        H, W = closed_pose(CARRY_H.translation + Vector((.004, -.004, -.006)) * u, CARRY_Q)
    elif t < 2.11:
        carry_end_H, carry_end_W = closed_pose(CARRY_H.translation + Vector((.004, -.004, -.006)), CARRY_Q)
        H, W = bridge(carry_end_H, carry_end_W, EXIT_H, EXIT_W,
                      (t - 1.85) / .26, (.012, .012, .030))
    elif t < 2.58:
        H, W = bridge(EXIT_H, EXIT_W, idle['hand_r'], idle['WPN_root'],
                      (t - 2.11) / .47, (.018, .040, .022))
    else:
        return idle['hand_r'].copy(), idle['WPN_root'].copy(), local_idle
    if t < CORE_START:
        amount = ease((t - .73) / (CORE_START - .73))
        fs = {n: mix(local_idle[n], FS0[n], amount) for n in fingers['r']}
    else:
        amount = ease((t - CORE_END) / (1.64 - CORE_END))
        fs = {n: mix(FS9[n], local_idle[n], amount) for n in fingers['r']}
    return H, W, fs


FREE_LEFT = idle['hand_l'].copy()
FREE_LEFT.translation = Vector(plan['left_free_wrist'])
LEFT_RELEASE = idle['hand_l'].copy()
LEFT_RELEASE.translation += Vector((-.055, -.020, -.020))
LEFT_APPROACH = idle['hand_l'].copy()
LEFT_APPROACH.translation += Vector((-.090, -.025, -.035))


def left_at(t):
    if t < .10:
        return idle['hand_l'].copy()
    if t < .24:
        return mix(idle['hand_l'], LEFT_RELEASE, ease((t - .10) / .14))
    if t < .50:
        return mix(LEFT_RELEASE, FREE_LEFT, ease((t - .24) / .26))
    if t < 2.35:
        return FREE_LEFT.copy()
    if t < 2.57:
        return mix(FREE_LEFT, LEFT_APPROACH, ease((t - 2.35) / .22))
    return mix(LEFT_APPROACH, idle['hand_l'], ease((t - 2.57) / .17))


def left_finger(n, t):
    digit = n.split('_')[0]
    release_start = {'thumb': 0., 'index': 0., 'middle': .015, 'ring': .030, 'pinky': .045}[digit]
    close = {'thumb': (2.74, 2.86), 'index': (2.70, 2.84), 'middle': (2.73, 2.87),
             'ring': (2.75, 2.90), 'pinky': (2.77, 2.93)}[digit]
    opening = ease((t - release_start) / .095) * (1 - ease((t - close[0]) / (close[1] - close[0])))
    loc, q, scale = local_idle[n].decompose()
    relaxed = local_rest[n].to_quaternion().slerp(q, .43)
    return Matrix.LocRotScale(loc, q.slerp(relaxed, opening), scale)


START_DEFORM = H0.to_quaternion() @ rest['hand_r'].to_quaternion().inverted()
ROLL_KEYS = [0., .12, .22, .35, .46, .52, .45, .34, .18, .08]


def core_guide(H, t):
    f = max(0., min(9., t * 30))
    i = min(8, int(f))
    amount = ROLL_KEYS[i] * (1 - (f - i)) + ROLL_KEYS[i + 1] * (f - i)
    hand_deform = H.to_quaternion() @ rest['hand_r'].to_quaternion().inverted()
    return START_DEFORM.slerp(hand_deform, amount)


CATCH_DEFORM = H9.to_quaternion() @ rest['hand_r'].to_quaternion().inverted()
CATCH_CORRECTION = CATCH_DEFORM.inverted() @ core_guide(H9, .3)


def arm_pose(side, H, t, active):
    un, fn, hn = [n + '_' + side for n in ('upperarm', 'lowerarm', 'hand')]
    if active <= 0.:
        return idle[un].copy(), idle[fn].copy()
    shoulder = idle[un].translation.copy()
    target = H.translation
    ru = rest[fn].translation - rest[un].translation
    rf = rest[hn].translation - rest[fn].translation
    l1, l2 = ru.length, rf.length
    reach = target - shoulder
    axis, dist = reach.normalized(), reach.length
    if dist > l1 + l2 - .014:
        shoulder += axis * (dist - (l1 + l2 - .014))
        dist = (target - shoulder).length
    driven = H.to_quaternion() @ rest[hn].to_quaternion().inverted()
    if side == 'r' and CORE_START <= t <= CORE_END:
        driven = core_guide(H, t - CORE_START)
    elif side == 'r' and CORE_END < t < 1.64:
        correction = CATCH_CORRECTION.slerp(Quaternion(), ease((t - CORE_END) / (1.64 - CORE_END)))
        driven = driven @ correction
    ideal = target - (driven @ rf.normalized()) * l2
    hint = ideal - shoulder
    hint -= axis * hint.dot(axis)
    # The right elbow drops inward; the spin is right-front of the body and
    # outside this forearm. Merely translating the sword would lose that relation.
    direction = Vector((-.85 if side == 'r' else -.7, .05, -1.))
    direction -= axis * direction.dot(axis)
    direction.normalize()
    pole = hint.normalized().lerp(direction, .72 if side == 'r' else .42).normalized()
    old_pole = idle[fn].translation - shoulder
    old_pole -= axis * old_pole.dot(axis)
    pole = old_pole.normalized().lerp(pole, active).normalized()
    along = (l1*l1 - l2*l2 + dist*dist) / (2 * max(dist, .0001))
    elbow = shoulder + axis*along + pole*math.sqrt(max(0., l1*l1 - along*along))
    fore_axis = (target - elbow).normalized()
    upper_axis = (elbow - shoulder).normalized()
    fore_deform = (driven @ rf.normalized()).rotation_difference(fore_axis) @ driven
    fq = fore_deform @ rest[fn].to_quaternion()
    uq = ((fore_deform @ ru.normalized()).rotation_difference(upper_axis) @ fore_deform
          @ rest[un].to_quaternion())
    old_upper = (idle[fn].translation - idle[un].translation).normalized()
    old_fore = (idle[hn].translation - idle[fn].translation).normalized()
    uq = (old_upper.rotation_difference(upper_axis) @ idle[un].to_quaternion()).slerp(uq, active)
    fq = (old_fore.rotation_difference(fore_axis) @ idle[fn].to_quaternion()).slerp(fq, active)
    return Matrix.LocRotScale(shoulder, uq, ONE), Matrix.LocRotScale(elbow, fq, ONE)


def pose_at(t):
    if t <= 0. or t >= DURATION:
        return {n: m.copy() for n, m in idle.items()}
    H, W, fs = right_at(t)
    p = {n: m.copy() for n, m in idle.items()}
    p['WPN_root'] = W
    for n in ('Blade_Base', 'Blade_Tip'):
        p[n] = W @ idle['WPN_root'].inverted() @ idle[n]
    for side, hand in (('r', H), ('l', left_at(t))):
        un, fn, hn = [n + '_' + side for n in ('upperarm', 'lowerarm', 'hand')]
        active = (ease((t - .18) / .27) * (1 - ease((t - 2.58) / .42)) if side == 'r'
                  else ease((t - .10) / .40) * (1 - ease((t - 2.74) / .26)))
        p[un], p[fn] = arm_pose(side, hand, t, active)
        upper_delta, fore_delta = p[un] @ idle[un].inverted(), p[fn] @ idle[fn].inverted()
        p['clavicle_' + side] = upper_delta @ idle['clavicle_' + side]
        # Transport each complete helper segment with its owner; no fractional
        # twist or weight/rest-bone edits are introduced.
        for segment, delta in (('upperarm', upper_delta), ('lowerarm', fore_delta)):
            for number in ('01', '02'):
                n = f'{segment}_twist_{number}_{side}'
                p[n] = delta @ idle[n]
        p[hn] = hand
        for n in fingers[side]:
            p[n] = p[parent[n]] @ (fs[n] if side == 'r' else left_finger(n, t))
    return p


old_action = bpy.data.actions.get('A_RuneSword_Inspect')
if old_action:
    old_action.name = 'RETAINED_V36_A_RuneSword_Inspect'
    old_action.use_fake_user = True
action = bpy.data.actions.new('A_RuneSword_Inspect')
action.use_fake_user = True
r.animation_data.action = action
previous = {}
for frame in range(round(DURATION * FPS) + 1):
    p = pose_at(frame / FPS)
    for n, b in r.pose.bones.items():
        local_pose = p[parent[n]].inverted() @ p[n] if parent[n] else p[n]
        loc, q, scale = (local_rest[n].inverted() @ local_pose).decompose()
        if n in previous and q.dot(previous[n]) < 0:
            q.negate()
        previous[n] = q.copy()
        b.rotation_mode = 'QUATERNION'
        b.location, b.rotation_quaternion, b.scale = loc, q, scale
        for channel in ('location', 'rotation_quaternion', 'scale'):
            b.keyframe_insert(channel, frame=frame, group=n)
r.animation_data.action_slot = action.slots[0]
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for key in curve.keyframe_points:
                    key.interpolation = 'LINEAR'
s.render.fps, s.render.fps_base = FPS, 1.
s.frame_start, s.frame_end = 0, round(DURATION * FPS)
s.frame_set(0)
bpy.ops.object.select_all(action='DESELECT')
r.hide_set(False)
r.select_set(True)
bpy.context.view_layer.objects.active = r
bpy.ops.export_scene.fbx(filepath=str(OUT / 'A_RuneSword_Inspect.fbx'), use_selection=True,
    object_types={'ARMATURE'}, axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
    bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
    bake_anim_simplify_factor=0)
for marker in list(s.timeline_markers):
    s.timeline_markers.remove(marker)
for label, t in [('Front idle / left release', 0.), ('Right side lift', .18),
                 ('Shoulder back carry', .73), ('V36 native spin start', CORE_START),
                 ('Palm open', CORE_START + .2), ('Catch', CORE_END),
                 ('Caught shoulder carry', 1.64), ('Lift blade before return', 1.85),
                 ('Front idle weapon stopped', 2.58), ('Left palm contact', 2.74),
                 ('Left fingers closed', 2.93), ('Exact project idle', DURATION)]:
    s.timeline_markers.new(label, frame=round(t * FPS))
r['ShoulderOutsideInspectV37'] = 'Front idle, outside shoulder bridge, V36 finger/contact core, delayed left regrip'
note = bpy.data.texts.new('SHOULDER_OUTSIDE_V37_README')
note.write('Current action: A_RuneSword_Inspect, 3.00 seconds, 120 fps.\n'
           'Retained actions: RETAINED_V36_A_RuneSword_Inspect and A_RuneSword_Reference_76_78.\n'
           'Native finger/contact core: video 76.0-76.3 at action 1.00-1.30.\n'
           'Plane yaw and transitions are a project adaptation, not unchanged source reproduction.\n'
           'No rendered, playback, collision or gameplay testing performed.\n')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'AzureRunesword_ShoulderOutsideV37.blend'))
(P / 'authoring.json').write_text(json.dumps({
    'revision': plan['revision'], 'source_blend': str(SOURCE),
    'reference_data': str(V36 / 'reference_poses.json'), 'duration': DURATION, 'fps': FPS,
    'core_source_seconds': [76.0, 76.3], 'core_game_seconds': [CORE_START, CORE_END],
    'spin_plane_yaw_degrees': plan['spin_plane_yaw_degrees'],
    'contact_method': 'Common rigid frame for V36 hand and sword; original finger-local data',
    'transition_method': 'Closed-grip wrist paths through shoulder and upright side gates',
    'forearm_method': 'Inward and downward elbow pole; V21 whole-segment helper transport',
    'ordinary_idle': 'Original front two-hand grip at both endpoints',
    'mesh_rest_weights_changed': False,
    'testing': 'Not rendered, played or tested; user testing pending'
}, indent=2), encoding='utf-8')
print('SHOULDER_OUTSIDE_V37_AUTHORING_COMPLETE', flush=True)
