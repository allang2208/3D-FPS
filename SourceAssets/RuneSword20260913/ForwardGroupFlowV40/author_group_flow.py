"""Move the V39 whole-group motion forward while retaining its articulation.

The evaluated V36 animation is the source. Every source bone receives the same
rigid transform at a given frame, preserving its internal articulation and the
changing hand/weapon contact. No arm, wrist or finger solver is run.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

P = Path(__file__).parent
V36 = P.parent / 'ReferenceReplicaV36'
SOURCE = V36 / 'AzureRunesword_ReferenceReplicaV36.blend'
plan = json.loads((P / 'motion_plan.json').read_text(encoding='utf-8'))
inputs = json.loads((V36 / 'authoring_inputs.json').read_text())
FPS, DURATION = plan['fps'], plan['duration']
ENTRY, REF_END = plan['reference_start'], plan['reference_end']
DT = 1. / FPS
ONE = Vector((1., 1., 1.))
OUT = P / 'Export'
OUT.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
s = bpy.context.scene
r = bpy.data.objects[inputs['rig']]
source_action = bpy.data.actions['A_RuneSword_Inspect']
r.animation_data.action = source_action
r.animation_data.action_slot = source_action.slots[0]
parents = {b.name: b.parent.name if b.parent else None for b in r.data.bones}
rest = {b.name: b.matrix_local.copy() for b in r.data.bones}
local_rest = {n: rest[parents[n]].inverted() @ m if parents[n] else m for n, m in rest.items()}

# Read the actual baked V36 action, including its existing arm support and
# helper-bone tracks. This is authoring input, not a newly solved approximation.
source_poses = []
for frame in range(round(DURATION * FPS) + 1):
    s.frame_set(frame)
    evaluated = r.evaluated_get(bpy.context.evaluated_depsgraph_get())
    source_poses.append({b.name: b.matrix.copy() for b in evaluated.pose.bones})


def ease(x):
    x = max(0., min(1., x))
    return max(0., min(1., x*x*x*(x*(6*x - 15) + 10)))


def mix(a, b, u):
    u = max(0., min(1., u))
    return Matrix.LocRotScale(a.translation.lerp(b.translation, u),
                              a.to_quaternion().slerp(b.to_quaternion(), u), ONE)


def source_hand(t):
    f = max(0., min(DURATION * FPS, t * FPS))
    i = min(len(source_poses) - 2, int(f))
    return mix(source_poses[i]['hand_r'], source_poses[i + 1]['hand_r'], f - i)


PIVOT = source_hand(ENTRY).translation.copy()
YAW = math.radians(plan['group_yaw_degrees'])
FORWARD = plan['group_forward_meters']


def group_turn(weight):
    q = Quaternion(Vector((0., 0., 1.)), YAW * weight)
    # +Y is the camera's forward direction in this authoring space. Apply the
    # offset after the common yaw so it moves forward, not along the tilted sword.
    forward = Matrix.Translation(Vector((0., FORWARD * weight, 0.)))
    return forward @ Matrix.Translation(PIVOT) @ q.to_matrix().to_4x4() @ Matrix.Translation(-PIVOT)


CORE_GROUP = group_turn(1.)


def nominal_hand(t):
    # Feed both the common turn and forward offset into the same flow curves.
    if t < ENTRY:
        weight = ease(t / ENTRY)
    elif t > REF_END:
        weight = 1. - ease((t - REF_END) / (DURATION - REF_END))
    else:
        weight = 1.
    return group_turn(weight) @ source_hand(t)


def rot_log(q):
    q = q.normalized()
    if q.w < 0.:
        q.negate()
    axis, angle = q.to_axis_angle()
    return axis * angle


def rot_exp(v):
    angle = v.length
    return Quaternion(v / angle, angle) if angle > 1.e-9 else Quaternion()


def derivative(t, direction=0):
    center = nominal_hand(t)
    q = center.to_quaternion()
    if direction > 0:
        after = nominal_hand(t + DT)
        velocity = (after.translation - center.translation) / DT
        angular = rot_log(q.inverted() @ after.to_quaternion()) / DT
    elif direction < 0:
        before = nominal_hand(t - DT)
        velocity = (center.translation - before.translation) / DT
        angular = -rot_log(q.inverted() @ before.to_quaternion()) / DT
    else:
        before, after = nominal_hand(t - DT), nominal_hand(t + DT)
        velocity = (after.translation - before.translation) / (2. * DT)
        angular = (rot_log(q.inverted() @ after.to_quaternion())
                   - rot_log(q.inverted() @ before.to_quaternion())) / (2. * DT)
    return velocity, angular


def make_bridge(start, end, start_side=0, end_side=0):
    a, b = nominal_hand(start), nominal_hand(end)
    va, wa = derivative(start, start_side)
    vb, wb = derivative(end, end_side)
    length = end - start
    qa, qb = a.to_quaternion(), b.to_quaternion()
    return {'start': start, 'end': end, 'a': a, 'b': b, 'va': va, 'vb': vb,
            'rotations': (qa, qa @ rot_exp(wa * (length / 3.)),
                          qb @ rot_exp(-wb * (length / 3.)), qb)}


# The entrance ends with the forward velocity of the V36 spin; the exit starts
# with the outgoing V36 velocity. Neither junction is eased down to a stop.
ENTRY_BRIDGE = make_bridge(*plan['entry_flow_window'], end_side=1)
EXIT_BRIDGE = make_bridge(*plan['exit_flow_window'], start_side=-1)


def bridge_hand(bridge, t):
    length = bridge['end'] - bridge['start']
    u = max(0., min(1., (t - bridge['start']) / length))
    u2, u3 = u*u, u*u*u
    position = ((2*u3 - 3*u2 + 1) * bridge['a'].translation
                + (u3 - 2*u2 + u) * length * bridge['va']
                + (-2*u3 + 3*u2) * bridge['b'].translation
                + (u3 - u2) * length * bridge['vb'])
    qa, ca, cb, qb = bridge['rotations']
    a, b, c = qa.slerp(ca, u), ca.slerp(cb, u), cb.slerp(qb, u)
    q = a.slerp(b, u).slerp(b.slerp(c, u), u)
    return Matrix.LocRotScale(position, q, ONE)


def frame_group(frame):
    t = frame / FPS
    if frame == 0 or frame == len(source_poses) - 1:
        return Matrix.Identity(4)
    if ENTRY <= t <= REF_END:
        return CORE_GROUP.copy()
    if ENTRY_BRIDGE['start'] <= t < ENTRY_BRIDGE['end']:
        desired = bridge_hand(ENTRY_BRIDGE, t)
    elif EXIT_BRIDGE['start'] < t <= EXIT_BRIDGE['end']:
        desired = bridge_hand(EXIT_BRIDGE, t)
    else:
        desired = nominal_hand(t)
    return desired @ source_poses[frame]['hand_r'].inverted()


source_action.name = 'RETAINED_V36_A_RuneSword_Inspect'
source_action.use_fake_user = True
action = bpy.data.actions.new('A_RuneSword_Inspect')
action.use_fake_user = True
r.animation_data.action = action
previous = {}
for frame, source_pose in enumerate(source_poses):
    group = frame_group(frame)
    # A common left multiplication preserves inverse(H)*W, inverse(parent)*bone
    # and every V36 finger-to-hand relationship at this frame.
    pose = {n: group @ m for n, m in source_pose.items()}
    for n, bone in r.pose.bones.items():
        local_pose = pose[parents[n]].inverted() @ pose[n] if parents[n] else pose[n]
        loc, q, scale = (local_rest[n].inverted() @ local_pose).decompose()
        if n in previous and q.dot(previous[n]) < 0.:
            q.negate()
        previous[n] = q.copy()
        bone.rotation_mode = 'QUATERNION'
        bone.location, bone.rotation_quaternion, bone.scale = loc, q, scale
        for channel in ('location', 'rotation_quaternion', 'scale'):
            bone.keyframe_insert(channel, frame=frame, group=n)
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
for label, t in [('Original idle', 0.), ('Entrance flow bridge', .25),
                 ('V36 reference / whole group turned', ENTRY), ('V36 open palm', ENTRY + .2),
                 ('V36 catch', ENTRY + .3), ('Exit flow bridge', REF_END),
                 ('Flow joins original recovery', 2.45), ('Original idle', DURATION)]:
    s.timeline_markers.new(label, frame=round(t * FPS))
r['ForwardGroupFlowV40'] = 'V39 direction with 0.24 m common forward placement and blended entrance/exit velocities'
note = bpy.data.texts.new('FORWARD_GROUP_FLOW_V40_README')
note.write('Source: retained V36 full A_RuneSword_Inspect, 2.90 seconds at 120 fps.\n'
           'All arms, fingers, helpers and sword receive the same frame transform.\n'
           'No V36 internal bone or hand/weapon relationship is separately reauthored.\n'
           'Common yaw: 65 degrees. Original two-second source timing retained.\n'
           'Forward placement: 0.24 m along global +Y, eased from and back to the original idle.\n'
           'Entry/exit use velocity-matched short group bridges, with no added hold poses.\n'
           'No playback, render or game testing performed.\n')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'AzureRunesword_ForwardGroupFlowV40.blend'))
(P / 'authoring.json').write_text(json.dumps({
    'revision': plan['revision'], 'source_blend': str(SOURCE),
    'source_action': source_action.name, 'duration': DURATION, 'fps': FPS,
    'group_yaw_degrees': plan['group_yaw_degrees'], 'group_pivot': list(PIVOT),
    'group_forward_meters': FORWARD, 'forward_axis': 'Global authoring +Y',
    'source_frames_used': len(source_poses),
    'relationship_method': 'P40[n,t] = common_group[t] @ baked_V36[n,t] for every bone',
    'entry_flow_window': plan['entry_flow_window'], 'exit_flow_window': plan['exit_flow_window'],
    'new_ik_or_finger_solver': False, 'retimed': False, 'added_hold_poses': False,
    'mesh_rest_weights_changed': False,
    'testing': 'No playback, render or game testing performed; user feedback pending'
}, indent=2), encoding='utf-8')
print('FORWARD_GROUP_FLOW_V40_AUTHORING_COMPLETE', flush=True)
