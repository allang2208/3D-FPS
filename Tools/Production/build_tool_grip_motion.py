"""Author single-hand harvest tools from the accepted Manny/VRE grasp.

Blender background production only: no game tests or acceptance renders.
The CC0 first-person melee donor informs preparation/swing/recovery and supplies
low-amplitude idle motion; the axe and pickaxe arcs below are newly authored.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/ProductionToolGrip20260913'
EXPORT = OUT / 'Export'
EXPORT.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT / 'SourceAssets/MannyGraspDonor20260912'
DONOR = ROOT / 'SourceAssets/RuneSword20260913/Reference'
motion = json.loads((DONOR / 'motion.json').read_text())
FPS = 150  # Exact keys at 0.24 s contact and 0.68 s end.
CLIPS = {'Idle': 1.6, 'Walk': .8, 'Equip': .32, 'Swing': .68, 'HitRecover': .44}


def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[-1]


def export(name, objects, animated=False):
    select(objects)
    bpy.ops.export_scene.fbx(filepath=str(EXPORT / name), use_selection=True,
        object_types={'ARMATURE', 'MESH'}, axis_forward='-Y', axis_up='Z',
        add_leaf_bones=False, bake_anim=animated, bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0,
        mesh_smooth_type='FACE', use_tspace=True)


def smooth(t):
    t = min(1., max(0., t))
    return t * t * (3 - 2 * t)


def frame(position, angles):
    x, y, z = (math.radians(a) for a in angles)
    return Matrix.Translation(position) @ Matrix.Rotation(z, 4, 'Z') @ Matrix.Rotation(y, 4, 'Y') @ Matrix.Rotation(x, 4, 'X')


def mix(a, b, t):
    return Matrix.LocRotScale(a.translation.lerp(b.translation, t),
        a.to_quaternion().slerp(b.to_quaternion(), t), Vector((1, 1, 1)))


report = {'runtime_tested': False, 'grasp_source': str(SOURCE),
          'motion_reference_commit': (DONOR / 'COMMIT.txt').read_text().strip(), 'tools': {}}
for kind in ['Axe', 'Pickaxe']:
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE / 'Final/m4/vertical/A_M4_Vertical_idle.blend'))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    scene.frame_set(0)
    rig = bpy.data.objects['SK_M4_Infima']
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
    local_rest = {b.name: rest[b.parent.name].inverted() @ rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
    fit = json.loads((SOURCE / 'Opening/0.8/aligned_fit.json').read_text())
    reflection = Matrix.Diagonal((-1, 1, 1, 1))
    grip = pose['WPN_root'] @ Matrix(fit['grip_in_root'])
    mirrored_grip = reflection @ grip @ reflection
    fingers = [b.name for b in rig.pose.bones if b.name.endswith('_l') and b.name.startswith(('index', 'middle', 'ring', 'pinky', 'thumb'))]
    mirrored = {n[:-1] + 'r': reflection @ (pose[n] @ rest[n].inverted()) @ reflection @ rest[n[:-1] + 'r'] for n in ['hand_l'] + fingers}
    right_relative = {n: mirrored['hand_r'].inverted() @ m for n, m in mirrored.items() if n != 'hand_r'}
    # The existing donor grip origin is above the fingers; center its palm wrap.
    hand_in_grip = Matrix.Translation((0, 0, .06)) @ mirrored_grip.inverted() @ mirrored['hand_r']
    for obj in list(scene.objects):
        if obj not in [rig, arms]:
            bpy.data.objects.remove(obj, do_unlink=True)
    rig.animation_data_clear()
    for bone in rig.pose.bones:
        for constraint in list(bone.constraints):
            bone.constraints.remove(constraint)
        bone.matrix_basis = Matrix.Identity(4)
    rig.name = 'SK_Harvest_' + kind + '_Rig'
    for modifier in arms.modifiers:
        if modifier.type == 'ARMATURE':
            modifier.object = rig

    filename = 'Axe.fbx' if kind == 'Axe' else 'Pickaxe_LOD0.fbx'
    bpy.ops.import_scene.fbx(filepath=str(ROOT / 'SourceAssets/FreeProductionTools20260913/UE' / filename))
    tool = next(obj for obj in scene.objects if obj.type == 'MESH' and obj != arms)
    tool.data.transform(tool.matrix_world)
    tool.matrix_world = Matrix.Identity(4)
    grip_z = -.26 if kind == 'Axe' else -.21
    # The axe handle curves away from its bounds center: use its actual grip section.
    section = [v.co for v in tool.data.vertices if abs(v.co.z - grip_z) < .06]
    center = Vector(((min(v.x for v in section) + max(v.x for v in section)) * .5,
                     (min(v.y for v in section) + max(v.y for v in section)) * .5, grip_z))
    tool.data.transform(Matrix.Translation(-center))
    tool.data.materials.clear()
    tool.data.materials.append(bpy.data.materials.new('M_Harvest_' + kind))
    tool.data.transform(rest['WPN_root'])
    tool.parent = rig
    group = tool.vertex_groups.new(name='WPN_root')
    group.add(list(range(len(tool.data.vertices))), 1., 'REPLACE')
    modifier = tool.modifiers.new('Rigid tool to shared grip motion', 'ARMATURE')
    modifier.object = rig
    tool.name = 'Harvest_' + kind
    rig.data.pose_position = 'REST'
    export('SK_Harvest_' + kind + '.fbx', [arms, tool, rig])
    rig.data.pose_position = 'POSE'

    axe = kind == 'Axe'
    ready = frame((.22, .42, -.30), (-35, -5, -12) if axe else (-29, 0, -8))
    windup = frame((.31, .27, -.12) if axe else (.25, .27, -.09), (-3, 18, -30) if axe else (22, 3, -8))
    impact = frame((.17, .49, -.29) if axe else (.20, .49, -.31), (-91, -15, 26) if axe else (-98, -2, 4))
    follow = frame((.07, .50, -.39) if axe else (.18, .52, -.41), (-112, -23, 38) if axe else (-118, -3, 6))
    retract = frame((.27, .32, -.36), (-55, -7, 5) if axe else (-56, 0, -4))
    rebound = frame((.21, .43, -.25) if axe else (.21, .43, -.23), (-76, -12, 20) if axe else (-77, -1, 3))
    hold = .0333333333 if axe else .0466666667

    def support(side, hand):
        upper, fore, wrist = [prefix + '_' + side for prefix in ['upperarm', 'lowerarm', 'hand']]
        anchor = rest[upper].translation
        target = hand.translation
        l1 = (rest[fore].translation - anchor).length
        l2 = (rest[wrist].translation - rest[fore].translation).length
        neutral = (hand.to_quaternion() @ rest[wrist].to_quaternion().inverted()) @ (rest[wrist].translation - rest[fore].translation).normalized()
        ideal = target - neutral * l2
        preferred = anchor + Vector((0, .07, -.02))
        shoulder = ideal + (preferred - ideal).normalized() * l1
        offset = shoulder - anchor
        offset.x = max(-.10, min(.10, offset.x))
        offset.y = max(-.04, min(.20, offset.y))
        offset.z = max(-.10, min(.08, offset.z))
        shoulder = anchor + offset
        axis = (target - shoulder).normalized()
        distance = (target - shoulder).length
        if distance > l1 + l2 - .015:
            shoulder += axis * (distance - (l1 + l2 - .015))
            distance = (target - shoulder).length
        pole = ideal - shoulder
        pole -= axis * pole.dot(axis)
        down = Vector((.55 if side == 'r' else -.55, -.15, -1))
        down -= axis * down.dot(axis)
        pole = (pole.normalized() * .94 + down.normalized() * .06).normalized()
        along = (l1*l1 - l2*l2 + distance*distance) / (2*distance)
        elbow = shoulder + axis * along + pole * math.sqrt(max(0., l1*l1 - along*along))
        bend = (target - elbow).normalized().angle(neutral)
        return bend*bend*.045 + (shoulder - preferred).length_squared*1.8, shoulder, elbow, target

    # Choose one cylindrical grip roll in the ready pose and keep it for the whole stroke.
    angles = [math.radians(a) for a in range(-180, 1, 3)]
    roll = min(angles, key=lambda a: support('r', ready @ Matrix.Rotation(a, 4, 'Z') @ hand_in_grip)[0])
    grasp = Matrix.Rotation(roll, 4, 'Z') @ hand_in_grip
    twist_history = {}

    def solve_arm(p, side, hand):
        upper, fore, wrist = [prefix + '_' + side for prefix in ['upperarm', 'lowerarm', 'hand']]
        _, shoulder, elbow, target = support(side, hand)
        p['clavicle_' + side].translation += shoulder - rest[upper].translation
        for name, start, end, old_end in [(upper, shoulder, elbow, rest[fore].translation), (fore, elbow, target, rest[wrist].translation)]:
            q = (old_end - rest[name].translation).normalized().rotation_difference((end - start).normalized()) @ rest[name].to_quaternion()
            p[name] = Matrix.LocRotScale(start, q, Vector((1, 1, 1)))
        neutral = p[fore].to_quaternion() @ rest[fore].to_quaternion().inverted() @ rest[wrist].to_quaternion()
        delta = hand.to_quaternion() @ neutral.inverted()
        axis = (target - elbow).normalized()
        twist = (2*math.atan2(Vector((delta.x, delta.y, delta.z)).dot(axis), delta.w) + math.pi) % (2*math.pi) - math.pi
        previous = twist_history.get(side, twist)
        while twist - previous > math.pi:
            twist -= 2*math.pi
        while twist - previous < -math.pi:
            twist += 2*math.pi
        twist_history[side] = twist
        neutral_forearm = p[fore].copy()
        p[fore] = Matrix.LocRotScale(elbow, Quaternion(axis, twist) @ neutral_forearm.to_quaternion(), Vector((1, 1, 1)))
        for prefix, parent in [('upperarm', upper), ('lowerarm', fore)]:
            for index in ['01', '02']:
                name = f'{prefix}_twist_{index}_{side}'
                if name not in rest:
                    continue
                base = neutral_forearm if prefix == 'lowerarm' else p[parent]
                m = base @ rest[parent].inverted() @ rest[name]
                if prefix == 'lowerarm':
                    weight = (rest[name].translation - rest[fore].translation).length / (rest[wrist].translation - rest[fore].translation).length
                    m = Matrix.LocRotScale(m.translation, Quaternion(axis, twist*weight) @ m.to_quaternion(), Vector((1, 1, 1)))
                p[name] = m
        p[wrist] = hand
        for bone in rig.pose.bones:
            name = bone.name
            if name in right_relative and side == 'r':
                location = p[bone.parent.name] @ local_rest[name].translation
                p[name] = Matrix.LocRotScale(location, hand.to_quaternion() @ right_relative[name].to_quaternion(), Vector((1, 1, 1)))
            elif side == 'l' and name in fingers:
                p[name] = p[bone.parent.name] @ local_rest[name]

    def apply(tool_frame):
        p = {n: m.copy() for n, m in rest.items()}
        solve_arm(p, 'r', tool_frame @ grasp)
        # The free arm rests down by the side, with a small counterbalance from the shoulder.
        free = rest['hand_l'].copy()
        free.translation = Vector((-.23, .04, -.53)) + (tool_frame.translation - ready.translation) * -.07
        solve_arm(p, 'l', free)
        p['WPN_root'] = tool_frame
        for bone in rig.pose.bones:
            bone.matrix_basis = local_rest[bone.name].inverted() @ (p[bone.parent.name].inverted() @ p[bone.name] if bone.parent else p[bone.name])
        bpy.context.view_layer.update()

    def swing(t):
        if t < .13:
            return mix(ready, windup, smooth(t/.13))
        if t < .24:
            return mix(windup, impact, ((t-.13)/.11)**2)
        if t < .32:
            return mix(impact, follow, 1-(1-(t-.24)/.08)**2)
        if t < .47:
            return mix(follow, retract, smooth((t-.32)/.15))
        return mix(retract, ready, smooth((t-.47)/.21))

    idle_data = motion['Sword_Idle']
    idle_origin = Matrix(idle_data[0]['right']).translation
    for clip, duration in CLIPS.items():
        action = bpy.data.actions.new(f'A_Harvest_{kind}_{clip}')
        action.use_fake_user = True
        rig.animation_data_create()
        rig.animation_data.action = action
        scene.render.fps = FPS
        scene.render.fps_base = 1
        scene.frame_start = 0
        scene.frame_end = round(duration * FPS)
        previous_quats = {}
        twist_history.clear()
        for f in range(scene.frame_end + 1):
            scene.frame_set(f)
            t = f/FPS
            if clip == 'Swing':
                sf = swing(t)
            elif clip == 'HitRecover':
                if t <= hold:
                    sf = impact.copy()
                elif t < .13:
                    sf = mix(impact, rebound, 1-(1-(t-hold)/(.13-hold))**3)
                elif t < .26:
                    sf = mix(rebound, retract, smooth((t-.13)/.13))
                else:
                    sf = mix(retract, ready, smooth((t-.26)/.18))
                # A decaying pulse through the shared hand/tool frame, not finger jitter.
                pulse = math.exp(-28*t)*math.sin(2*math.pi*20*t)*math.sin(math.pi*min(1,t/.20))**2
                sf = Matrix.Translation((0, -.0035*pulse, .0015*pulse)) @ sf
            elif clip == 'Equip':
                start = Matrix.Translation((.035, -.08, -.32)) @ ready @ Matrix.Rotation(math.radians(-35), 4, 'X')
                sf = mix(start, ready, smooth(t/duration))
            elif clip == 'Walk':
                phase = 2*math.pi*t/duration
                sf = Matrix.Translation((.005*math.sin(phase), .003*math.sin(phase*2), -.007*(1-math.cos(phase*2)))) @ ready
            else:
                x = t/duration * (len(idle_data)-1)
                i = min(int(x), len(idle_data)-2)
                offset = Matrix(idle_data[i]['right']).translation.lerp(Matrix(idle_data[i+1]['right']).translation, x-i) - idle_origin
                offset *= .18 * math.sin(math.pi*t/duration)**2
                sf = Matrix.Translation((-offset.x, -offset.y, offset.z)) @ ready
            apply(sf)
            for bone in rig.pose.bones:
                bone.rotation_mode = 'QUATERNION'
                q = bone.rotation_quaternion.copy()
                if bone.name in previous_quats and q.dot(previous_quats[bone.name]) < 0:
                    q.negate()
                bone.rotation_quaternion = q
                previous_quats[bone.name] = q.copy()
                for property_name in ['location', 'rotation_quaternion', 'scale']:
                    bone.keyframe_insert(property_name, frame=f, group=bone.name)
        export(f'A_Harvest_{kind}_{clip}.fbx', [rig], True)
        print('AUTHORED', kind, clip, duration, flush=True)
    rig.animation_data.action = bpy.data.actions[f'A_Harvest_{kind}_Idle']
    rig.animation_data.action_slot = rig.animation_data.action.slots[0]
    scene.frame_end = round(CLIPS['Idle']*FPS)
    scene.frame_set(0)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / f'{kind}_SingleHand_Editable.blend'))
    report['tools'][kind] = {'mesh': f'SK_Harvest_{kind}', 'clips': CLIPS,
        'fps': FPS, 'contact_seconds': .24, 'hit_hold_seconds': hold,
        'grip_center_in_static_mesh_m': list(center), 'grasp_roll_degrees': math.degrees(roll)}
(OUT / 'authoring.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
