"""Make the requested default-idle-position sword spin.

Both wrist/elbow relationships come from the accepted idle. The right arm does
not follow the sword rotation. The left arm leaves through its shoulder only.
This script authors and exports; it does not render or test the animation.
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
reference = json.loads((V36 / 'reference_poses.json').read_text())
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


def depth(n):
    return 1 + depth(parent[n]) if parent[n] else 0


def in_chain(n, root):
    while n:
        if n == root:
            return True
        n = parent[n]
    return False


fingers = {side: sorted([n for n in rest if n.endswith('_' + side) and
                       n.startswith(('thumb', 'index', 'middle', 'ring', 'pinky'))], key=depth)
           for side in ('l', 'r')}
left_chain = [n for n in rest if in_chain(n, 'upperarm_l')]


def ease(x):
    x = max(0., min(1., x))
    return max(0., min(1., x*x*x*(x*(6*x - 15) + 10)))


def mix(a, b, w):
    w = max(0., min(1., w))
    return Matrix.LocRotScale(a.translation.lerp(b.translation, w),
                              a.to_quaternion().slerp(b.to_quaternion(), w), ONE)


# The native orientations retain the V36 turn sequence, while slowly removing
# its start-to-catch carry-angle drift. Both endpoints now meet the same idle
# sword orientation without making the wrist follow that drift.
native = [{'hand': Matrix(row['hand_r']), 'weapon': Matrix(row['weapon']),
           'fingers': {n: Matrix(m) for n, m in row['finger_local'].items()}}
          for row in reference['frames'][:10]]
IDLE_H, IDLE_W = idle['hand_r'], idle['WPN_root']
start_alignment = IDLE_W.to_quaternion() @ native[0]['weapon'].to_quaternion().inverted()
end_alignment = IDLE_W.to_quaternion() @ native[9]['weapon'].to_quaternion().inverted()

# V36's authored palm contact stations. These are construction anchors, not
# measured skin contacts. Preserve their phase changes with the V36 fingers.
A = Vector((.0285727177, .102494739, .994323134))
L = Vector((-.994306445, .105071038, .017741533))
N = A.cross(L)
SUPPORT = {
    1: (.036, .064, .019), 2: (.041, .061, .022),
    3: (.047, .056, .024), 4: (.050, .054, .023),
    5: (.052, .052, .023), 6: (.052, .054, .024),
    7: (.047, .060, .024), 8: (.040, .065, .021),
}
spin_keys = []
for i, source in enumerate(native):
    H, W = source['hand'], source['weapon']
    alignment = start_alignment.slerp(end_alignment, ease(i / 9.))
    q = alignment @ W.to_quaternion()
    if i in SUPPORT:
        a, longitudinal, normal = SUPPORT[i]
        hand_anchor = A*a + L*longitudinal + N*normal
        weapon_anchor = W.inverted() @ (H @ hand_anchor)
    else:
        # Closed phases use the exact accepted hilt-to-palm relation.
        weapon_anchor = Vector((0., 0., -.077))
        hand_anchor = IDLE_H.inverted() @ (IDLE_W @ weapon_anchor)
        q = IDLE_W.to_quaternion()
    spin_keys.append({'q': q, 'hand_anchor': hand_anchor,
                      'weapon_anchor': weapon_anchor, 'fingers': source['fingers']})


def sword_at(t):
    if t <= CORE_START or t >= CORE_END:
        return IDLE_W.copy(), local_idle
    f = (t - CORE_START) / (CORE_END - CORE_START) * 9.
    i = min(8, int(f))
    u = max(0., min(1., f - i))
    a, b = spin_keys[i], spin_keys[i + 1]
    q = a['q'].slerp(b['q'], u)
    hand_anchor = a['hand_anchor'].lerp(b['hand_anchor'], u)
    weapon_anchor = a['weapon_anchor'].lerp(b['weapon_anchor'], u)
    # Keep the current support station on the unchanged idle hand. The sword
    # orientation is free; its origin is derived from this contact, not orbited
    # independently. No right arm target or wrist twist is solved here.
    position = IDLE_H @ hand_anchor - q @ weapon_anchor
    W = Matrix.LocRotScale(position, q, ONE)
    fs = {n: mix(a['fingers'][n], b['fingers'][n], u) for n in fingers['r']}
    return W, fs


LEFT_ROT = (Quaternion(Vector((1, 0, 0)), -math.radians(plan['left_shoulder_downward_degrees']))
            @ Quaternion(Vector((0, 0, 1)), math.radians(plan['left_shoulder_outward_degrees'])))
LEFT_SHOULDER = idle['upperarm_l'].translation.copy()


def left_transform(t):
    amount = ease((t - .12) / .28) * (1. - ease((t - 1.) / .45))
    q = Quaternion().slerp(LEFT_ROT, amount)
    # One common rigid transform for upper arm, forearm, wrist and their helpers.
    # Their internal joint relationships stay at the original idle values.
    return Matrix.Translation(LEFT_SHOULDER) @ q.to_matrix().to_4x4() @ Matrix.Translation(-LEFT_SHOULDER)


def left_finger(n, t):
    digit = n.split('_')[0]
    release = {'thumb': 0., 'index': 0., 'middle': .015, 'ring': .030, 'pinky': .045}[digit]
    close = {'thumb': (1.47, 1.60), 'index': (1.43, 1.57), 'middle': (1.46, 1.61),
             'ring': (1.48, 1.63), 'pinky': (1.50, 1.65)}[digit]
    opening = ease((t - release) / .095) * (1. - ease((t - close[0]) / (close[1] - close[0])))
    loc, q, scale = local_idle[n].decompose()
    relaxed = local_rest[n].to_quaternion().slerp(q, .43)
    return Matrix.LocRotScale(loc, q.slerp(relaxed, opening), scale)


def pose_at(t):
    p = {n: m.copy() for n, m in idle.items()}
    if t <= 0. or t >= DURATION:
        return p
    W, right_fingers = sword_at(t)
    p['WPN_root'] = W
    for n in ('Blade_Base', 'Blade_Tip'):
        p[n] = W @ IDLE_W.inverted() @ idle[n]
    left_delta = left_transform(t)
    for n in left_chain:
        p[n] = left_delta @ idle[n]
    for side in ('r', 'l'):
        for n in fingers[side]:
            p[n] = p[parent[n]] @ (right_fingers[n] if side == 'r' else left_finger(n, t))
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
        if n in previous and q.dot(previous[n]) < 0.:
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
for label, t in [('Default idle / left release', 0.), ('Left shoulder outward', .12),
                 ('Left clear', .4), ('Spin at original idle grip', CORE_START),
                 ('Right fingers open', CORE_START + .2), ('Catch at idle', CORE_END),
                 ('Left return', 1.), ('Left palm contact', 1.45),
                 ('Left fingers closed', 1.65), ('Default two-hand idle', DURATION)]:
    s.timeline_markers.new(label, frame=round(t * FPS))
r['DefaultIdleInspectV38'] = 'Right arm and wrist remain at idle; sword and fingers turn at the idle grip'
note = bpy.data.texts.new('DEFAULT_IDLE_V38_README')
note.write('A_RuneSword_Inspect: 1.80 seconds at 120 fps.\n'
           'Spin: 0.50-0.80 seconds, using V36 native orientation/finger phases.\n'
           'Right shoulder, elbow, forearm, wrist and arm helpers stay at accepted idle.\n'
           'Left arm moves as one idle-shaped chain through the shoulder.\n'
           'This changes the reference wrist choreography to match the user request.\n'
           'No rendered or game testing performed.\n')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'AzureRunesword_DefaultIdleV38.blend'))
(P / 'authoring.json').write_text(json.dumps({
    'revision': plan['revision'], 'source_blend': str(SOURCE),
    'source_data': str(V36 / 'reference_poses.json'), 'duration': DURATION, 'fps': FPS,
    'spin_game_seconds': [CORE_START, CORE_END], 'spin_source_seconds': [76., 76.3],
    'right_arm_method': 'Exact idle transforms, without IK or wrist rotation',
    'left_arm_method': 'Common shoulder rotation, preserving idle elbow and wrist relationships',
    'sword_method': 'Native orientation sequence corrected to same idle endpoints, moving support stations',
    'finger_method': 'V36 individual finger-local poses, original closed-grip endpoints',
    'mesh_rest_weights_changed': False,
    'testing': 'No playback, render or game testing performed; user trial pending'
}, indent=2), encoding='utf-8')
print('DEFAULT_IDLE_V38_AUTHORING_COMPLETE', flush=True)
