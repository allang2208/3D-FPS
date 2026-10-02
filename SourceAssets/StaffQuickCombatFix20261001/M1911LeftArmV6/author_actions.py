"""Re-author the six M1911 left-strike clips with continuous wrist support.

Background Blender production only. The accepted V7 native bare arm is included
in the editable source, but exports remain animation-only on the native rig.
"""
import ast
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2]
OLD = PROJECT / 'SourceAssets/DualPistolQuickCombat20260920/SpinRecoveryV5'
V3 = OLD.parent / 'VideoRefV3'
SOURCE = OLD / 'M1911/l/M1911_l_QuickCombat_Editable.blend'
WEAPON, LEAD, SIDE = 'M1911', 'l', 'l'
MOTION = json.loads((V3 / 'motion.json').read_text(encoding='utf-8'))
sys.path.insert(0, str(OLD))
from recovery_solver import PROFILES, smooth, window, support_twist, relax_fingers, spin_gun

# Read the original trajectory and exact native-length arm functions without
# executing their asset-production loops or modifying any old source.
tree = ast.parse((V3 / 'author_actions.py').read_text(encoding='utf-8'))
functions = {'camera', 'turn', 'source_keyed', 'keyed', 'flow_tangents', 'solve_arm'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                             and n.name in functions], type_ignores=[]),
             'V3_trajectory_helpers', 'exec'), globals())
FLOW_TANGENTS = {(s, c): flow_tangents(MOTION[s]['times'], MOTION[s][c])
                 for s in ('r', 'l') for c in ('position', 'angles', 'shoulder', 'elbow')}


def load_source():
    bpy.context.preferences.filepaths.save_version = 0
    try:
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    except RuntimeError as error:
        if 'Missing library override hierarchy root data' not in str(error):
            raise
    rig = bpy.data.objects['SK_M1911_Manny']
    rig.data.pose_position = 'POSE'
    rig.animation_data_create()
    return rig


def native_v7_arm(rig, rest):
    """Register the accepted surface through each native inverse bind matrix."""
    family = PROJECT / 'SourceAssets/ModularOutfit20260925'
    accepted = family / 'BarePalmV7/Authored/M1911_l.json'
    data = json.loads(accepted.read_text(encoding='utf-8'))
    native = json.loads((family / 'BareArmsFamilyV6/Sources/M1911_l.json').read_text(encoding='utf-8'))
    transforms = {}
    for n in {n for weights in data['weights'] for n in weights}:
        bone = native['bones'][n]
        matrix = Matrix(bone['axes']).transposed().to_4x4()
        matrix.translation = Vector(bone['position'])
        transforms[n] = rest[n] @ matrix.inverted()
    points = []
    for point, weights in zip(data['positions'], data['weights']):
        p = Vector(point)
        points.append(sum(((transforms[n] @ p) * weight
                           for n, weight in weights.items()), Vector((0., 0., 0.))))
    mesh = bpy.data.meshes.new('M1911_l_AcceptedBarePalmV7')
    mesh.from_pydata(points, [], data['triangles'])
    mesh.update()
    obj = bpy.data.objects.new('M1911_l_AcceptedBarePalmV7', mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = rig
    modifier = obj.modifiers.new('NativeM1911Binding', 'ARMATURE')
    modifier.object = rig
    for n in sorted(transforms):
        obj.vertex_groups.new(name=n)
    for vi, weights in enumerate(data['weights']):
        for n, weight in weights.items():
            obj.vertex_groups[n].add([vi], weight, 'REPLACE')
    skin = bpy.data.materials.new('V7_SkinAuthoringPreview')
    skin.diffuse_color = (.372, .232, .182, 1.)
    skin.use_nodes = True
    node = next((n for n in skin.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if node is None:
        node = skin.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
        output = next((n for n in skin.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)
        if output is None:
            output = skin.node_tree.nodes.new('ShaderNodeOutputMaterial')
        skin.node_tree.links.new(node.outputs['BSDF'], output.inputs['Surface'])
    node.inputs['Base Color'].default_value = skin.diffuse_color
    node.inputs['Roughness'].default_value = .49
    mesh.materials.append(skin)
    uv = mesh.uv_layers.new(name='NativeSkinUV')
    for face, corners in zip(mesh.polygons, data['uv']):
        face.use_smooth = True
        for loop, (u, v) in zip(face.loop_indices, corners):
            uv.data[loop].uv = (u, 1. - v)
    # Preserve the source's arm object instead of removing historical data.
    original = bpy.data.objects.get('Manny_Dual_l')
    if original:
        original.hide_render = True
        original.hide_set(True)
    obj['AcceptedSurface'] = str(accepted)
    obj['Binding'] = 'Per-bone native inverse bind registration; no shared M4 bind substitution'
    obj['Material'] = 'Authoring preview only; runtime V7 skin materials are unchanged'
    lower = rest['lowerarm_l'].translation
    axis = rest['hand_l'].translation - lower
    values = {n: [] for n in ('lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l')}
    for point, weights in zip(points, data['weights']):
        dominant = max(weights, key=weights.get)
        if dominant in values:
            values[dominant].append((point - lower).dot(axis) / axis.length_squared)
    stations = {n: max(0., min(1., sorted(v)[len(v)//2])) if v else 0.
                for n, v in values.items()}
    stations['lowerarm_l'] = 0.  # Hinge support at the elbow, not palm roll.
    return stations


def elbow_circle(idle, hand, shoulder, pole_target, neutral):
    upper, lower, wrist = (idle[n].translation for n in ('upperarm_l', 'lowerarm_l', 'hand_l'))
    l1, l2 = (lower - upper).length, (wrist - lower).length
    target = hand.translation
    delta = target - shoulder
    distance = delta.length
    axis = delta.normalized()
    reach = (l1 + l2) * .985
    if distance > reach:
        shoulder += axis * (distance - reach)
        distance = reach
    distance = max(abs(l1 - l2) + .0001, distance)
    along = (l1*l1 - l2*l2 + distance*distance) / (2. * distance)
    center = shoulder + axis * along
    radius = math.sqrt(max(0., l1*l1 - along*along))
    pole = pole_target - shoulder
    pole -= axis * pole.dot(axis)
    if pole.length < 1e-7:
        pole = (lower - upper).cross(wrist - lower).cross(axis)
    pole.normalize()
    desired = target - neutral * l2 - center
    desired -= axis * desired.dot(axis)
    if desired.length > 1e-7:
        desired.normalize()
        angle = math.atan2(axis.dot(pole.cross(desired)), pole.dot(desired))
        # Keep the original elbow side; do not flip to the opposite solution.
        pole = Quaternion(axis, max(-math.radians(48.), min(math.radians(48.), angle))) @ pole
    return shoulder, center + pole * radius


def supported_hand(idle, hand, shoulder, pole, weight):
    """Correct the held hand+gun base throughout the attack, including contact.

    The wrist's accepted idle relationship defines its neutral support axis.
    Correction is solved with the actual native elbow circle and then fed back
    into the elbow plane. The external gun flourish remains an independent
    whole revolution and never rotates the arm by 360 degrees.
    """
    idle_fore = (idle['hand_l'].translation - idle['lowerarm_l'].translation).normalized()
    idle_q = idle['hand_l'].to_quaternion()
    result = hand.copy()
    for _ in range(7):
        neutral = result.to_quaternion() @ idle_q.inverted() @ idle_fore
        shoulder, elbow = elbow_circle(idle, result, shoulder.copy(), pole, neutral)
        fore = (result.translation - elbow).normalized()
        bend = neutral.angle(fore)
        excess = max(0., bend - math.radians(22.))
        if excess < 1e-6 or weight < 1e-7:
            break
        correction = neutral.rotation_difference(fore)
        rotation = Quaternion().slerp(correction, excess / max(bend, 1e-7) * weight)
        result = Matrix.LocRotScale(result.translation, rotation @ result.to_quaternion(), result.to_scale())
    neutral = result.to_quaternion() @ idle_q.inverted() @ idle_fore
    shoulder, elbow = elbow_circle(idle, result, shoulder.copy(), pole, neutral)
    return result, shoulder, elbow


rig = load_source()
scene = bpy.context.scene
scene.render.fps = 60
names = [b.name for b in rig.data.bones]
parents = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
local_rest = {n: rest[parents[n]].inverted() @ rest[n] if parents[n] else rest[n] for n in names}
stations = native_v7_arm(rig, rest)
destination = OUT / 'M1911/l'
(destination / 'Animations').mkdir(parents=True, exist_ok=True)
receipt = {
    'weapon': WEAPON, 'revision': 'M1911LeftArmV6', 'source': str(SOURCE),
    'duration': .8, 'contact': .18, 'sample_rate': 120, 'loop': False,
    'spin_window': [.435, .675], 'left_strike_only': True,
    'wrist_support': 'Idle-calibrated forearm support; 22 degree target on full attack including contact',
    'elbow_plane_limit_degrees': 48., 'upperarm_twist_share': .32,
    'upperarm_twist_limit_degrees': 38., 'skin_stations': stations,
    'native_bare_arm': 'BarePalmV7/Authored/M1911_l.json',
    'testing': 'No renders or runtime tests; user testing', 'clips': {}}
actions = {}
for profile_name, profile in PROFILES.items():
    for empty in (False, True):
        suffix = '_empty' if empty else ''
        idle_name = f'Dual_M1911_l_idle{suffix}'
        idle_action = bpy.data.actions[idle_name]
        rig.animation_data.action = idle_action
        rig.animation_data.action_slot = idle_action.slots[0]
        scene.frame_set(0)
        bpy.context.view_layer.update()
        idle = {b.name: b.matrix.copy() for b in rig.pose.bones}
        grip = idle['WPN_root'].inverted() @ idle['hand_l']
        gun_local = {n: idle['WPN_root'].inverted() @ idle[n] for n in names if n.startswith('WPN_')}
        rows, frames, previous, state = [], [], {}, {}
        for index in range(97):
            t = index / 120.
            p = {n: m.copy() for n, m in idle.items()}
            position, angles = keyed(SIDE, 'position', t), keyed(SIDE, 'angles', t)
            flourish = window(t, .32, .445, .66, .765)
            position += Vector((profile['forward'], -profile['outward'], .008)) * flourish
            pivot = idle['hand_l'].translation
            transform = Matrix.Translation(pivot + camera(position)) @ turn(angles).to_matrix().to_4x4() @ Matrix.Translation(-pivot)
            root = transform @ idle['WPN_root']
            hand = root @ grip
            shoulder = idle['upperarm_l'].translation + camera(keyed(SIDE, 'shoulder', t))
            pole = idle['lowerarm_l'].translation + camera(keyed(SIDE, 'elbow', t))
            if index not in (0, 96):
                shoulder += camera((.008, -.010, 0.)) * flourish
                # A single support envelope: full support before contact, held
                # across the recovery and smoothly returned to the actual idle.
                support = window(t, 0., .055, .70, .80)
                hand, shoulder, pole = supported_hand(idle, hand, shoulder, pole, support)
                root = hand @ grip.inverted()
                solve_arm(p, idle, SIDE, hand, shoulder, pole, names)
                support_twist(p, idle, rest, SIDE, stations, support, state)
                relax_fingers(p, idle, SIDE, t, profile, parents, local_rest)
                root = spin_gun(root, p, idle, rest, SIDE, t, profile, WEAPON, camera)
            for n, local in gun_local.items():
                p[n] = root @ local
            row = {}
            for n in names:
                local = p[parents[n]].inverted() @ p[n] if parents[n] else p[n]
                loc, q, scale = (local_rest[n].inverted() @ local).decompose()
                if n in previous and previous[n].dot(q) < 0:
                    q.negate()
                previous[n] = q.copy()
                row[n] = (loc, q, scale)
            rows.append(row)
            frames.append(t * 60.)
        kind = 'quickcombat_left' + profile['suffix'] + suffix
        action = bpy.data.actions.new('V6_Dual_M1911_l_' + kind)
        action.use_fake_user = True
        action['contact_seconds'] = .18
        action['duration_seconds'] = .8
        action['left_wrist_support_revision'] = 'M1911LeftArmV6'
        rig.animation_data.action = action
        for n in names:
            bone = rig.pose.bones[n]
            bone.rotation_mode = 'QUATERNION'
            for prop in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(prop, frame=0.)
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
        scene.frame_start, scene.frame_end = 0, 48
        scene.frame_set(0)
        bpy.ops.object.select_all(action='DESELECT')
        rig.hide_set(False)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        fbx = destination / 'Animations' / f'A_Dual_M1911_l_{kind}.fbx'
        bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'ARMATURE'},
            axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
            bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
            bake_anim_step=.5, bake_anim_simplify_factor=0.)
        receipt['clips'][kind] = {'fbx': str(fbx), 'action': action.name,
                                 'idle': idle_name, 'striking_hand': 'l', 'profile': profile_name}
        actions[kind] = action
        print('M1911_LEFT_ARM_V6_EXPORTED ' + kind, flush=True)
rig.animation_data.action = actions['quickcombat_left']
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_set(0)
for marker in list(scene.timeline_markers):
    scene.timeline_markers.remove(marker)
for name, t in [('STRIKE_CONTACT', .18), ('SPIN_BEGIN', .435), ('SPIN_END', .675), ('IDLE_HANDOFF', .8)]:
    scene.timeline_markers.new(name, frame=round(t * 60.))
blend = destination / 'M1911_l_QuickCombat_LeftArmV6_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
receipt['blend'] = str(blend)
(OUT / 'authoring.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print('M1911_LEFT_ARM_V6_AUTHOR_COMPLETE', flush=True)
