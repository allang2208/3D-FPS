"""Build the axe idle from tool-local contacts and complete Manny arm segments.

Blender --background --python build_horizontal_axe_idle_v2.py [-- horizontal_idle_v3.json]
No previews, tests, or changes to the other four production clips are performed.
Without a config argument this rebuilds H2. H3 preserves H2's hand approach while
turning the blade outward and adding small, independent palm clearances.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
config_name = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'horizontal_idle_v2.json'
CFG = json.loads((HERE / config_name).read_text(encoding='utf-8'))
REVISION = CFG.get('revision', 'H2')
OUT = HERE / CFG.get('output_dir', 'BuildH2')
EXPORT = OUT / 'Export'
EXPORT.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT / 'SourceAssets/BattleAxeReplace20260919/Viewmodel/BattleAxe_SingleHand_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
rig = bpy.data.objects['SK_Harvest_Axe_Rig']
tool = bpy.data.objects['Harvest_Axe']
rig.data.pose_position = 'POSE'
rig.animation_data.action = bpy.data.actions['A_Harvest_Axe_Idle']
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
local_rest = {b.name: rest[b.parent.name].inverted() @ rest[b.name] if b.parent else rest[b.name]
              for b in rig.data.bones}
source_pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
source_tool = source_pose['WPN_root']
source_tool_inv = source_tool.inverted()
fingers_r = [b.name for b in rig.data.bones if b.name.endswith('_r')
             and b.name.startswith(('index', 'middle', 'ring', 'pinky', 'thumb'))]

# Reflect positions through the tool plane, but map *deformation* through the
# anatomical rest frames. Conjugating an arbitrary bone frame by the tool plane
# alone does not account for the left and right bone-axis conventions.
mirror_rig = Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0))
mirror_tool = source_tool @ mirror_rig @ source_tool_inv
source_left = {}
for nr in ['hand_r'] + fingers_r:
    nl = nr[:-1] + 'l'
    mirrored = mirror_tool @ source_pose[nr] @ rest[nr].inverted() @ mirror_rig @ rest[nl]
    mirrored.translation = mirror_tool @ source_pose[nr].translation
    source_left[nl] = mirrored

donor_grip = {
    'r': source_tool_inv @ source_pose['hand_r'],
    'l': source_tool_inv @ source_left['hand_l'],
}
finger_relative = {
    'r': {n: source_pose['hand_r'].inverted() @ source_pose[n] for n in fingers_r},
    'l': {n: source_left['hand_l'].inverted() @ p for n, p in source_left.items() if n != 'hand_l'},
}

# Read the actual rigid axe geometry in WPN_root bind space, not its global bounds.
mesh_to_tool = rest['WPN_root'].inverted() @ rig.matrix_world.inverted() @ tool.matrix_world
vertices = [mesh_to_tool @ v.co for v in tool.data.vertices]


def section(z):
    points = [v for v in vertices if abs(v.z - z) < CFG['section_half_band_m']]
    low = Vector((min(p.x for p in points), min(p.y for p in points), z))
    high = Vector((max(p.x for p in points), max(p.y for p in points), z))
    return (low + high) * 0.5, (high - low) * 0.5


def section_frame(along):
    # Sample around the palm, with a local tangent for the curved wooden shaft.
    z = along + CFG['palm_section_offset_m']
    center, radii = section(z)
    before, _ = section(z - 0.02)
    after, _ = section(z + 0.02)
    tangent = (after - before).normalized()
    rotation = Vector((0, 0, 1)).rotation_difference(tangent)
    origin = center - rotation @ Vector((0, 0, CFG['palm_section_offset_m']))
    return Matrix.LocRotScale(origin, rotation, Vector((1, 1, 1))), radii


def ready_frame(config):
    # Angle is measured from down towards forward: 90 degrees faces away from
    # the player. Projection keeps the blade perpendicular to the tilted shaft.
    lean = math.radians(config['handle_lean_deg'])
    axis = Vector((math.cos(lean), config['handle_forward'], math.sin(lean))).normalized()
    blade_angle = math.radians(config['blade_forward_deg'])
    blade = Vector((0, math.sin(blade_angle), -math.cos(blade_angle)))
    blade = (blade - axis * blade.dot(axis)).normalized()
    side_axis = axis.cross(blade).normalized()
    rotation = Matrix((blade, side_axis, axis)).transposed().to_quaternion()
    return Matrix.LocRotScale(Vector(config['hold_origin_m']), rotation, Vector((1, 1, 1)))


ready = ready_frame(CFG)
contact_reference = None
if CFG.get('contact_reference'):
    contact_reference = json.loads((HERE / CFG['contact_reference']).read_text(encoding='utf-8'))
    reference_ready = ready_frame(contact_reference['config'])


def support(side, hand):
    upper, fore, wrist = [p + '_' + side for p in ('upperarm', 'lowerarm', 'hand')]
    shoulder = rest[upper].translation + Vector((0, CFG['shoulder_forward_m'], -CFG['shoulder_down_m']))
    target = hand.translation
    l1 = (rest[fore].translation - rest[upper].translation).length
    l2 = (rest[wrist].translation - rest[fore].translation).length
    reach = target - shoulder
    distance = reach.length
    direction = reach.normalized()
    # Shoulder support is continuous and preserves the two original bone lengths.
    shoulder += direction * max(0.0, distance - CFG['reach_fraction'] * (l1 + l2))
    distance = (target - shoulder).length
    down_out = Vector((CFG['elbow_outward'] * (1 if side == 'r' else -1),
                       CFG['elbow_backward'], -1.0))
    pole = (down_out - direction * down_out.dot(direction)).normalized()
    along = (l1 * l1 - l2 * l2 + distance * distance) / (2.0 * distance)
    elbow = shoulder + direction * along + pole * math.sqrt(max(0.0, l1 * l1 - along * along))
    hand_deform = hand.to_quaternion() @ rest[wrist].to_quaternion().inverted()
    neutral = hand_deform @ (rest[wrist].translation - rest[fore].translation).normalized()
    bend = neutral.angle((target - elbow).normalized())
    return shoulder, elbow, target, bend


# Fit whole-hand cylindrical roll once per hand in the base pose. No per-frame
# re-selection: the fitted tool-local contacts remain fixed throughout breathing.
grips = {}
grip_parameters = {}
base_section, base_radii = section_frame(0.0)
for side, along in [('r', CFG['right_grip_along_m']),
                    ('l', CFG['right_grip_along_m'] - CFG['grip_spacing_m'])]:
    fitted_section, radii = section_frame(along)
    donor = donor_grip[side].copy()

    def at_roll(degrees):
        turn = Matrix.Rotation(math.radians(degrees), 4, 'Z')
        grip = turn @ donor
        radial = Vector((grip.translation.x, grip.translation.y, 0)).normalized()
        # Preserve the accepted palm clearance when the local shaft radius changes.
        old_radial = Vector((donor.translation.x, donor.translation.y, 0)).normalized()
        old_radius = math.sqrt((base_radii.x * old_radial.x) ** 2 + (base_radii.y * old_radial.y) ** 2)
        new_radius = math.sqrt((radii.x * radial.x) ** 2 + (radii.y * radial.y) ** 2)
        grip.translation += radial * (new_radius - old_radius)
        return fitted_section @ grip

    def roll_cost(degrees):
        hand = ready @ at_roll(degrees)
        _, _, _, bend = support(side, hand)
        return bend * bend + 0.015 * math.radians(degrees) ** 2

    clearance = CFG.get('grip_clearance_m', {}).get(side, 0.0)
    if contact_reference:
        # Retain the user-approved H2 wrist approach instead of rotating the
        # arms with the blade or running another unconstrained roll search.
        reference = contact_reference['contacts'][side]
        old_section, old_radii = section_frame(reference['along_m'])
        old_section_world = reference_ready @ old_section
        new_section_world = ready @ fitted_section
        old_hand = reference_ready @ Matrix(reference['tool_local_hand'])
        old_tangent = (old_section_world.to_3x3() @ Vector((0, 0, 1))).normalized()
        new_tangent = (new_section_world.to_3x3() @ Vector((0, 0, 1))).normalized()
        tangent_swing = old_tangent.rotation_difference(new_tangent)
        offset = old_hand.translation - old_section_world.translation
        axial = offset.dot(old_tangent)
        old_radial = offset - old_tangent * axial
        new_radial = tangent_swing @ old_radial.normalized()
        old_direction = old_section_world.to_quaternion().inverted() @ old_radial.normalized()
        new_direction = new_section_world.to_quaternion().inverted() @ new_radial
        old_radius = math.sqrt((old_radii.x * old_direction.x) ** 2 + (old_radii.y * old_direction.y) ** 2)
        new_radius = math.sqrt((radii.x * new_direction.x) ** 2 + (radii.y * new_direction.y) ** 2)
        hand_position = (new_section_world.translation + new_tangent * axial
                         + new_radial * (old_radial.length + new_radius - old_radius + clearance))
        hand_rotation = tangent_swing @ old_hand.to_quaternion()
        grips[side] = ready.inverted() @ Matrix.LocRotScale(hand_position, hand_rotation, Vector((1, 1, 1)))
        roll = None
    else:
        roll = min(range(-180, 181, 3), key=roll_cost)
        grips[side] = at_roll(roll)
    grip_parameters[side] = {'along_m': along, 'roll_deg': roll,
                             'clearance_m': clearance,
                             'reference': CFG.get('contact_reference'),
                             'section_center_m': list(fitted_section.translation),
                             'section_half_width_m': list(radii),
                             'tool_local_hand': [list(row) for row in grips[side]]}


def solve_arm(pose, side, hand):
    upper, fore, wrist = [p + '_' + side for p in ('upperarm', 'lowerarm', 'hand')]
    shoulder, elbow, target, _ = support(side, hand)
    pose['clavicle_' + side].translation += shoulder - rest[upper].translation
    original_upper = (rest[fore].translation - rest[upper].translation).normalized()
    original_fore = (rest[wrist].translation - rest[fore].translation).normalized()
    upper_q = original_upper.rotation_difference((elbow - shoulder).normalized()) @ rest[upper].to_quaternion()
    pose[upper] = Matrix.LocRotScale(shoulder, upper_q, Vector((1, 1, 1)))
    # Same closed forearm construction as the project's current Manny casting rig.
    hand_deform = hand.to_quaternion() @ rest[wrist].to_quaternion().inverted()
    aligned = hand_deform @ original_fore
    fore_deform = aligned.rotation_difference((target - elbow).normalized()) @ hand_deform
    pose[fore] = Matrix.LocRotScale(elbow, fore_deform @ rest[fore].to_quaternion(), Vector((1, 1, 1)))
    for segment in (upper, fore):
        for index in ('01', '02'):
            helper = segment.replace('_' + side, '_twist_' + index + '_' + side)
            if helper in rest:
                pose[helper] = pose[segment] @ rest[segment].inverted() @ rest[helper]
    pose[wrist] = hand
    for bone in rig.pose.bones:
        if bone.name in finger_relative[side]:
            position = pose[bone.parent.name] @ local_rest[bone.name].translation
            q = hand.to_quaternion() @ finger_relative[side][bone.name].to_quaternion()
            pose[bone.name] = Matrix.LocRotScale(position, q, Vector((1, 1, 1)))


sway = json.loads((HERE / 'sway_s8888.json').read_text(encoding='utf-8'))['samples']
chest0_pos = Vector(sway[0]['Chest']['pos'])
chest0_quat = Quaternion(sway[0]['Chest']['quat'])
conversion = Matrix.Diagonal((-1.0, -1.0, 1.0))


def tool_frame(t):
    u = min(1.0, max(0.0, t / CFG['duration_s']))
    x = u * (len(sway) - 1)
    i = min(int(x), len(sway) - 2)
    f = x - i
    envelope = math.sin(math.pi * u) ** 2
    position = Vector(sway[i]['Chest']['pos']).lerp(Vector(sway[i + 1]['Chest']['pos']), f) - chest0_pos
    delta = chest0_quat.inverted() @ Quaternion(sway[i]['Chest']['quat']).slerp(Quaternion(sway[i + 1]['Chest']['quat']), f)
    offset = conversion @ position * (CFG['breathing_position_scale'] * envelope)
    mapped = conversion @ delta.to_matrix() @ conversion
    q = Quaternion().slerp(mapped.to_quaternion(), CFG['breathing_rotation_scale'] * envelope)
    pivot = ready.translation
    return Matrix.Translation(offset + pivot) @ q.to_matrix().to_4x4() @ Matrix.Translation(-pivot) @ ready


action = bpy.data.actions.new(CFG['name'])
action.use_fake_user = True
rig.animation_data.action = action
scene.render.fps = CFG['fps']
scene.render.fps_base = 1
scene.frame_start = 0
scene.frame_end = round(CFG['duration_s'] * CFG['fps'])
previous_quats = {}
for frame in range(scene.frame_end + 1):
    scene.frame_set(frame)
    wpn = tool_frame(frame / CFG['fps'])
    pose = {n: m.copy() for n, m in rest.items()}
    for side in ('r', 'l'):
        solve_arm(pose, side, wpn @ grips[side])
    pose['WPN_root'] = wpn
    for bone in rig.pose.bones:
        parent_inv = pose[bone.parent.name].inverted() if bone.parent else Matrix.Identity(4)
        bone.matrix_basis = local_rest[bone.name].inverted() @ parent_inv @ pose[bone.name]
    bpy.context.view_layer.update()
    for bone in rig.pose.bones:
        bone.rotation_mode = 'QUATERNION'
        q = bone.rotation_quaternion.copy()
        if bone.name in previous_quats and q.dot(previous_quats[bone.name]) < 0:
            q.negate()
        bone.rotation_quaternion = q
        previous_quats[bone.name] = q.copy()
        for property_name in ('location', 'rotation_quaternion', 'scale'):
            bone.keyframe_insert(property_name, frame=frame, group=bone.name)

# Store a camera matching the current non-sprint component origin, without rendering.
camera_data = bpy.data.cameras.new('ProductionToolCamera_' + REVISION)
camera_data.sensor_fit = 'HORIZONTAL'
camera_data.sensor_width = 36
camera_data.lens = 36 / (2 * math.tan(math.radians(CFG['camera_vertical_fov_deg'] / 2)) * 16 / 9)
camera = bpy.data.objects.new('ProductionToolCamera_' + REVISION, camera_data)
scene.collection.objects.link(camera)
camera.location = CFG['camera_origin_m']
camera.rotation_euler = (math.pi / 2, 0, 0)
scene.camera = camera
scene.render.resolution_x = 960
scene.render.resolution_y = 540
scene.render.resolution_percentage = 100
scene.frame_set(0)
for material in list(bpy.data.materials):
    if material.users == 0:
        bpy.data.materials.remove(material)
for image in list(bpy.data.images):
    if image.users == 0 or '.fbm' in (image.filepath or ''):
        bpy.data.images.remove(image)
bpy.ops.file.pack_all()
blend_out = OUT / (CFG['name'] + '_Editable.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(blend_out))
bpy.ops.object.select_all(action='DESELECT')
rig.hide_set(False)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
fbx_out = EXPORT / (CFG['name'] + '.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx_out), use_selection=True, object_types={'ARMATURE'},
                        axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
                        bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                        bake_anim_simplify_factor=0)
receipt = {'runtime_tested': False, 'rendered': False, 'source_blend': str(SOURCE),
           'config': CFG, 'contacts': grip_parameters, 'blend': str(blend_out), 'fbx': str(fbx_out),
           'scope': 'Idle only; Walk/Equip/Swing/HitRecover unchanged'}
(OUT / 'authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('AXE_HORIZONTAL_' + REVISION + '_AUTHORED ' + str(fbx_out), flush=True)
