"""Author AKM and QBZ191 one-handed tactical sprint using the accepted per-grip idle poses.

Blender --background --python author_sprint.py -- AKM|QBZ191 Base|Angled|Vertical|Canted|Prism
Produces editable Blender sources and animation-only FBX. Does not render or test.
"""
import ast
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector, Euler, Quaternion

O = Path(__file__).resolve().parent
S = O.parent
weapon, profile = sys.argv[sys.argv.index('--') + 1:sys.argv.index('--') + 3]
settings = json.loads((O / 'sources.json').read_text(encoding='utf-8'))[weapon]
record = json.loads((O / 'source-poses.json').read_text(encoding='utf-8'))[weapon + ':' + profile]
source, source_action = record['source'], record['action']
dest = O / weapon / profile
(dest / 'Animations').mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(S / source))
rig = bpy.data.objects['SK_M4_Infima']
rig.data.pose_position = 'POSE'
scene = bpy.context.scene
scene.render.fps = 60
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parent = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
names = list(rest)
lr = {n: rest[parent[n]].inverted() @ rest[n] if parent[n] else rest[n] for n in names}
action = bpy.data.actions[source_action]
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
idle = {b.name: b.matrix.copy() for b in rig.pose.bones}

tree = ast.parse((S / 'DanWesson71520260913/author_weapon.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                             and n.name == 'hand_at'], type_ignores=[]), '<full arm solver>', 'exec'))

def smooth(a, b, value):
    x = max(0., min(1., (value - a) / (b - a)))
    return x * x * (3. - 2. * x)

def turn(x, y, z):
    return Euler(tuple(math.radians(a) for a in (x, y, z)), 'XYZ').to_quaternion()

# Match the upright muzzle direction while keeping each weapon's original hold.
barrel = idle['WPN_SOCKET_Muzzle'].translation - idle['WPN_root'].translation
raise_pitch = 76. - math.degrees(math.atan2(barrel.z, math.hypot(barrel.x, barrel.y)))

def make_pose(progress, phase=None):
    pose = {n: m.copy() for n, m in idle.items()}
    released = smooth(0., .22, progress)
    raised = smooth(.25, 1., progress)
    withdrawn = smooth(.16, .82, progress)
    loop = phase is not None
    side = math.sin(phase) if loop else 0.
    step = math.cos(2 * phase) if loop else 0.
    # Rifle author coordinates: +Y forward, +X right, +Z up (metres).
    # Rotate the weapon around its bearing wrist; all weapon mechanical bones
    # and the right fingers share the same rigid delta.
    offset = Vector(settings['right_wrist_offset_m']) * raised
    offset += Vector((.007 * side, .009 * step, -.009 * step))
    rotation = Quaternion().slerp(turn(raise_pitch + 1.2 * side, -8 + 1.5 * side, -7 + .9 * step), raised)
    pivot = idle['hand_r'].translation
    delta = Matrix.Translation(pivot + offset) @ rotation.to_matrix().to_4x4() @ Matrix.Translation(-pivot)
    for n in names:
        if n.startswith('WPN_'):
            pose[n] = delta @ idle[n]
    hand_at(pose, idle, 'r', delta @ idle['hand_r'])

    # Unwrap and move down/out first, then swing independently of the rifle.
    origin = idle['hand_l'].translation
    clear = origin + Vector((-.045, -.005, -.055)) * released
    hang = settings.get('left_wrist_hang')
    if hang:
        # Natural hang, no folded arm: keep the chain near straight below the
        # shoulder (98% of full length, a ~23 deg soft elbow) instead of the
        # old chest-height pocket target that folded the arm to 44% reach and
        # swept the forearm across the lower frame. Swing is sin-only so the
        # Enter/Loop seam starts at zero.
        sh = idle['upperarm_l'].translation
        l1 = (idle['lowerarm_l'].translation - sh).length
        l2 = (idle['hand_l'].translation - idle['lowerarm_l'].translation).length
        dx, dy = hang['side_offset']
        if loop:
            sx, sy = hang['swing']
            dx += sx * side
            dy += sy * side
        d = hang['reach'] * (l1 + l2)
        dz = -math.sqrt(max(1e-4, d * d - dx * dx - dy * dy))
        target = sh + Vector((dx, dy, dz))
        # Swing the hand along a shoulder-centred arc with early extension. A
        # straight corner-cut lerp between the guard and the hang point dips
        # the reach to 0.74 and folds the elbow to ~86 deg mid-retract, which
        # reads as a folding arm. Slerping the direction while easing the
        # radius out within the first half keeps the chain near-straight all
        # the way down; the outward bias clears the gun and body.
        # The default withdrawn schedule (smooth .16-.82) barely moves inside
        # the on-screen window, so the through-hole grasps (Angled idles fold
        # ~75 deg) keep their fold while visible. Rebind to an earlier, faster
        # ramp so the arm opens as soon as the fingers clear.
        withdrawn = smooth(.10, .60, progress)
        t = withdrawn
        v0 = clear - sh
        v1 = target - sh
        r0, r1 = v0.length, v1.length
        d0, d1 = v0 / r0, v1 / r1
        ang = d0.angle(d1)
        axis = d0.cross(d1)
        if axis.length < 1e-6 or ang < 1e-6:
            dm = d0.lerp(d1, t).normalized()
        else:
            dm = Quaternion(axis.normalized(), ang * t) @ d0
        dm = (dm + Vector((-1., 0., 0.)) * .3 * math.sin(math.pi * t)).normalized()
        location = sh + dm * (r0 + (r1 - r0) * (1. - (1. - t) ** 4))
    else:
        # Leave margin below/behind the camera for the whole hand during the stride.
        target = Vector((-.26 - .008 * side, -.10 - .025 * side, -.36 + .010 * side))
        location = clear.lerp(target, withdrawn)
    q_rest_wrist = rest['lowerarm_l'].to_quaternion().inverted() @ rest['hand_l'].to_quaternion()
    q_idle_wrist = idle['lowerarm_l'].to_quaternion().inverted() @ idle['hand_l'].to_quaternion()
    if settings.get('left_wrist_relax'):
        # The AKM grip idles hold an extreme wrist (Base is the palm-up Soviet
        # under hold, ~107 deg from rest). Carrying that world orientation
        # through the pull inverts the wrist joint (~177 deg at full retract,
        # claw hand and a vertical forearm across the lower frame). Relax the
        # wrist JOINT toward rest instead and take the hand orientation from
        # the solved forearm, which is how the accepted M4/QBZ191 retract
        # reads. Two passes are exact: the forearm solve depends only on the
        # hand location, so the second pass only re-aims the hand.
        relax = settings['left_wrist_relax']
        amount = min(1., relax['released_share'] * released + relax['withdrawn_share'] * withdrawn)
        q_local = q_idle_wrist.slerp(q_rest_wrist, amount)
        hand_at(pose, idle, 'l', Matrix.LocRotScale(location, idle['hand_l'].to_quaternion(), idle['hand_l'].to_scale()))
        wrist = turn(5 * side, 0, 0) @ (pose['lowerarm_l'].to_quaternion() @ q_local)
    else:
        wrist = idle['hand_l'].to_quaternion()
        wrist = wrist.slerp(turn(-20 + 5 * side, 8, -16) @ wrist, withdrawn)
    hand_at(pose, idle, 'l', Matrix.LocRotScale(location, wrist, idle['hand_l'].to_scale()))
    # Relax finger rotations through their existing local chain. Preserve bone
    # lengths and metacarpals; no individual finger translation or hand scaling.
    finger_relax = settings.get('finger_relax', .52)
    for n in names:
        if n.endswith('_l') and n.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')) and '_metacarpal_' not in n:
            local = idle[parent[n]].inverted() @ idle[n]
            loc, q, scale = local.decompose()
            relaxed = q.slerp(lr[n].to_quaternion(), finger_relax * released)
            pose[n] = pose[parent[n]] @ Matrix.LocRotScale(loc, relaxed, scale)
    return pose

receipt = {'weapon': weapon, 'profile': profile, 'source': source, 'source_action': source_action,
           'coordinates': '+Y forward, +X right, +Z up; metres',
           'reference': 'M4TacticalSprint20260915 one-handed sprint; each rifle uses its accepted grip idle',
           'upright_pitch_delta': raise_pitch, 'right_wrist_offset_m': settings['right_wrist_offset_m'],
           'left_wrist_relax': settings.get('left_wrist_relax'),
           'left_wrist_hang': settings.get('left_wrist_hang'),
           'finger_relax': settings.get('finger_relax', .52),
           'status': 'Authored and exported; not rendered or tested', 'clips': {}}
for kind, end in [('Enter', 18), ('Loop', 36), ('Exit', 18)]:
    frames = [i * .5 for i in range(end * 2 + 1)]
    rows, previous = [], {}
    for frame in frames:
        t = frame / end
        # Exit follows the same pose path backwards so interrupted entry/exit
        # can reverse at the current progress without jumping to a new pose.
        pose = make_pose(1. if kind == 'Loop' else (1. - t if kind == 'Exit' else t),
                         2 * math.pi * t if kind == 'Loop' else None)
        row = {}
        for n in names:
            basis = lr[n].inverted() @ (pose[parent[n]].inverted() @ pose[n] if parent[n] else pose[n])
            loc, q, scale = basis.decompose()
            if n in previous and previous[n].dot(q) < 0:
                q.negate()
            previous[n] = q.copy()
            row[n] = (loc, q, scale)
        rows.append(row)
    action = bpy.data.actions.new(f'{weapon}_TacticalSprint_{profile}_{kind}')
    action.use_fake_user = True
    rig.animation_data.action = action
    for n in names:
        bone = rig.pose.bones[n]
        bone.rotation_mode = 'QUATERNION'
        for prop in ('location', 'rotation_quaternion', 'scale'):
            bone.keyframe_insert(prop, frame=0)
    curves = {(c.data_path, c.array_index): c for c in action.layers[0].strips[0].channelbag(action.slots[0]).fcurves}
    for n in names:
        for prop, field, count in [('location', 0, 3), ('rotation_quaternion', 1, 4), ('scale', 2, 3)]:
            for axis in range(count):
                curve = curves[(f'pose.bones["{n}"].{prop}', axis)]
                curve.keyframe_points.clear()
                curve.keyframe_points.add(len(frames))
                curve.keyframe_points.foreach_set('co', [v for f, row in zip(frames, rows) for v in (f, row[n][field][axis])])
                for key in curve.keyframe_points:
                    key.interpolation = 'LINEAR'
                curve.update()
    rig.animation_data.action_slot = action.slots[0]
    scene.frame_start, scene.frame_end = 0, end
    scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    fbx = dest / 'Animations' / f'A_{weapon}_TacticalSprint_{profile}_{kind}.fbx'
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'ARMATURE'},
        axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
        bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True, bake_anim_step=.5, bake_anim_simplify_factor=0)
    receipt['clips'][kind] = {'action': action.name, 'duration': end / 60., 'sample_rate': 120, 'fbx': str(fbx)}

rig.animation_data.action = bpy.data.actions[f'{weapon}_TacticalSprint_{profile}_Loop']
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_start, scene.frame_end = 0, 36
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(dest / f'{weapon}_TacticalSprint_{profile}_Editable.blend'))
(dest / 'authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('RIFLE_TACTICAL_SPRINT_AUTHORED', weapon, profile, flush=True)
