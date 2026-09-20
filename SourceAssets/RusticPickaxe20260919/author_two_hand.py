"""Fit the current axe H4/ThumbFix grip to the rustic pickaxe.

Idle and equip retain the accepted source timing and full arm construction.
Mining keeps its original 0.24 s contact / 0.68 s cycle with two-hand seams.
Walk/Run are editable stride references; runtime uses the same carry parameters
with the character's footstep phase, blended by movement speed.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'Export'
FPS = 150
AXE_SOURCE = ROOT / 'SourceAssets/AxeThumb20260919/Fixed/Axe_ThumbFix_Idle_Equip_Editable.blend'
MINING_SOURCE = ROOT / 'SourceAssets/ProductionToolGrip20260913/Pickaxe_SingleHand_Editable.blend'


def action_on(rig, name):
    action = bpy.data.actions[name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    return action


def read_tool_frames(rig, name, seconds):
    action_on(rig, name)
    result = []
    for frame in range(round(seconds * FPS) + 1):
        bpy.context.scene.frame_set(frame)
        result.append(rig.pose.bones['WPN_root'].matrix.copy())
    return result


def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[-1]


def export(name, objects, animated=False):
    select(objects)
    bpy.ops.export_scene.fbx(filepath=str(OUT / (name + '.fbx')), use_selection=True,
        object_types={'ARMATURE', 'MESH'}, axis_forward='-Y', axis_up='Z',
        add_leaf_bones=False, bake_anim=animated, bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0,
        mesh_smooth_type='FACE', use_tspace=True, path_mode='STRIP')


def ease(t):
    t = min(1., max(0., t))
    return t*t*t*(10.-15.*t+6.*t*t)


def mix(a, b, t):
    return Matrix.LocRotScale(a.translation.lerp(b.translation, t),
        a.to_quaternion().slerp(b.to_quaternion(), t), Vector((1, 1, 1)))


# Read the actual old mining path before opening the current two-hand source.
bpy.ops.wm.open_mainfile(filepath=str(MINING_SOURCE))
old_rig = bpy.data.objects['SK_Harvest_Pickaxe_Rig']
mining = {clip: read_tool_frames(old_rig, 'A_Harvest_Pickaxe_' + clip, duration)
          for clip, duration in (('Swing', .68), ('HitRecover', .44))}

bpy.ops.wm.open_mainfile(filepath=str(AXE_SOURCE))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
rig = bpy.data.objects['SK_Harvest_Axe_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']
old_tool = bpy.data.objects['Harvest_Axe']
idle = read_tool_frames(rig, 'A_Harvest_Axe_Idle', 3.)
equip = read_tool_frames(rig, 'A_Harvest_Axe_Equip', .48)
action_on(rig, 'A_Harvest_Axe_Idle')
scene.frame_set(0)
ready = rig.pose.bones['WPN_root'].matrix.copy()
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
local_rest = {b.name: rest[b.parent.name].inverted() @ rest[b.name] if b.parent else rest[b.name]
              for b in rig.data.bones}
baseline = {b.name: b.matrix.copy() for b in rig.pose.bones}
finger_basis = {b.name: b.matrix_basis.copy() for b in rig.pose.bones
                if b.name.startswith(('thumb', 'index', 'middle', 'ring', 'pinky'))}
old_to_tool = rest['WPN_root'].inverted() @ rig.matrix_world.inverted() @ old_tool.matrix_world
old_points = [old_to_tool @ vertex.co for vertex in old_tool.data.vertices]
bpy.data.objects.remove(old_tool, do_unlink=True)

bpy.ops.import_scene.fbx(filepath=str(OUT / 'RusticPickaxe_Viewmodel.fbx'))
tool = next(obj for obj in scene.objects if obj.type == 'MESH' and obj != arms)
tool.data.transform(tool.matrix_world)
tool.matrix_world = Matrix.Identity(4)
# The mesh remains 84 cm long. Recenter on its real shaft near the lower grip,
# not the asymmetrical pick head's bounding-box centre.
grip_z = -.26
section_points = [v.co for v in tool.data.vertices if abs(v.co.z - grip_z) < .02]
origin = Vector(((min(p.x for p in section_points) + max(p.x for p in section_points))*.5,
                 (min(p.y for p in section_points) + max(p.y for p in section_points))*.5, grip_z))
tool.data.transform(Matrix.Translation(-origin))
new_points = [vertex.co.copy() for vertex in tool.data.vertices]


def section(points, z):
    band = [p for p in points if abs(p.z - z) < .012]
    low = Vector((min(p.x for p in band), min(p.y for p in band), z))
    high = Vector((max(p.x for p in band), max(p.y for p in band), z))
    return (low + high)*.5, (high - low)*.5


def section_frame(points, along):
    centre, radii = section(points, along + .045)
    before, _ = section(points, along + .025)
    after, _ = section(points, along + .065)
    tangent = (after - before).normalized()
    rotation = Vector((0, 0, 1)).rotation_difference(tangent)
    return Matrix.LocRotScale(centre - rotation @ Vector((0, 0, .045)), rotation, Vector((1, 1, 1))), radii


grips = {}
grip_report = {}
for side, along in (('l', .08), ('r', .30)):
    old_section, old_radii = section_frame(old_points, along)
    new_section, new_radii = section_frame(new_points, along)
    old_hand = ready.inverted() @ baseline['hand_' + side]
    tangent_old = old_section.to_quaternion() @ Vector((0, 0, 1))
    tangent_new = new_section.to_quaternion() @ Vector((0, 0, 1))
    align = tangent_old.rotation_difference(tangent_new)
    offset = old_hand.translation - old_section.translation
    axial = offset.dot(tangent_old)
    radial = offset - tangent_old*axial
    direction_old = old_section.to_quaternion().inverted() @ radial.normalized()
    direction_new = new_section.to_quaternion().inverted() @ (align @ radial.normalized())
    old_radius = math.hypot(old_radii.x*direction_old.x, old_radii.y*direction_old.y)
    new_radius = math.hypot(new_radii.x*direction_new.x, new_radii.y*direction_new.y)
    # Keep the source palm clearance and its anatomically fitted approach angle.
    position = new_section.translation + tangent_new*axial + (align @ radial.normalized())*(radial.length + new_radius - old_radius)
    grips[side] = Matrix.LocRotScale(position, align @ old_hand.to_quaternion(), Vector((1, 1, 1)))
    # Close the existing grasp mildly on the thinner handle; never move/scale
    # finger bones or independently fit fingertips at the expense of joint shape.
    closure = min(1., max(0., (old_radius - new_radius) / .013))
    curls = {}
    for name, basis in list(finger_basis.items()):
        if not name.endswith('_' + side) or 'metacarpal' in name:
            continue
        amount = 0.
        if name.startswith('thumb'):
            if '_02_' in name or '_03_' in name:
                amount = 3.5 * closure
        elif '_01_' in name:
            amount = 2. * closure
        elif '_02_' in name:
            amount = 10. * closure
        elif '_03_' in name:
            amount = 6. * closure
        if amount:
            q = basis.to_quaternion()
            sign = 1. if q.to_euler('XYZ').z >= 0 else -1.
            finger_basis[name] = Matrix.LocRotScale(basis.translation,
                q @ Quaternion((0, 0, 1), math.radians(amount*sign)), basis.to_scale())
            curls[name] = amount*sign
    grip_report[side] = {'shaft_radius_m': new_radius, 'previous_radius_m': old_radius,
        'tool_local_hand': [list(row) for row in grips[side]], 'additional_curl_degrees': curls}

tool.data.transform(rest['WPN_root'])
tool.parent = rig
tool.name = 'Harvest_Pickaxe'
group = tool.vertex_groups.new(name='WPN_root')
group.add(list(range(len(tool.data.vertices))), 1., 'REPLACE')
modifier = tool.modifiers.new('Rigid two-hand tool', 'ARMATURE')
modifier.object = rig
rig.name = 'SK_RusticPickaxe_Rig'
rig.data.pose_position = 'REST'
export('SK_RusticPickaxe', [arms, tool, rig])
rig.data.pose_position = 'POSE'


def solve_arm(pose, side, hand):
    upper, fore, wrist = [part + '_' + side for part in ('upperarm', 'lowerarm', 'hand')]
    shoulder = rest[upper].translation + Vector((0, .025, -.015))
    target = hand.translation
    l1 = (rest[fore].translation - rest[upper].translation).length
    l2 = (rest[wrist].translation - rest[fore].translation).length
    reach = target - shoulder
    direction = reach.normalized()
    shoulder += direction * max(0., reach.length - .93*(l1+l2))
    distance = (target - shoulder).length
    down = Vector((.45 if side == 'r' else -.45, -.15, -1))
    pole = (down - direction*down.dot(direction)).normalized()
    along = (l1*l1-l2*l2+distance*distance)/(2*distance)
    elbow = shoulder + direction*along + pole*math.sqrt(max(0., l1*l1-along*along))
    original_upper = (rest[fore].translation-rest[upper].translation).normalized()
    original_fore = (rest[wrist].translation-rest[fore].translation).normalized()
    upper_q = original_upper.rotation_difference((elbow-shoulder).normalized()) @ rest[upper].to_quaternion()
    hand_deform = hand.to_quaternion() @ rest[wrist].to_quaternion().inverted()
    fore_deform = (hand_deform @ original_fore).rotation_difference((target-elbow).normalized()) @ hand_deform
    pose['clavicle_' + side].translation += shoulder-rest[upper].translation
    pose[upper] = Matrix.LocRotScale(shoulder, upper_q, Vector((1, 1, 1)))
    pose[fore] = Matrix.LocRotScale(elbow, fore_deform @ rest[fore].to_quaternion(), Vector((1, 1, 1)))
    for segment in (upper, fore):
        for index in ('01', '02'):
            helper = segment.replace('_' + side, '_twist_' + index + '_' + side)
            if helper in rest:
                pose[helper] = pose[segment] @ rest[segment].inverted() @ rest[helper]
    pose[wrist] = hand
    for bone in rig.pose.bones:
        if bone.name.endswith('_' + side) and bone.name in finger_basis:
            pose[bone.name] = pose[bone.parent.name] @ local_rest[bone.name] @ finger_basis[bone.name]


def mining_frame(clip, frame, time):
    # Existing mining arc shifted along the shaft for the new pair of grips.
    # Return seams meet the new idle; the original contact time stays at .24 s.
    result = mining[clip][frame] @ Matrix.Translation((0, 0, -.18))
    if clip == 'Swing' and time < .13:
        first = mining[clip][0] @ Matrix.Translation((0, 0, -.18))
        result = mix(ready @ first.inverted() @ result, result, ease(time/.13))
    tail_start, end = (.47, .68) if clip == 'Swing' else (.26, .44)
    if time > tail_start:
        final = mining[clip][-1] @ Matrix.Translation((0, 0, -.18))
        result = mix(result, ready @ final.inverted() @ result, ease((time-tail_start)/(end-tail_start)))
    return result


CLIPS = {'Idle': 3., 'Equip': .48, 'Swing': .68, 'HitRecover': .44, 'Walk': .8, 'Run': .64}
carry = {'Walk': {'travel_cm': [.3, .7, .5], 'angles_degrees': [.3, .3, .55]},
         'Run': {'travel_cm': [.55, 2.3, 1.35], 'angles_degrees': [1., 1., 2.]}}
report = {'revision': 'RusticPickaxe_TwoHand1', 'idle_equip_reference': str(AXE_SOURCE),
          'mining_reference': str(MINING_SOURCE), 'fps': FPS, 'clips': CLIPS,
          'contact_seconds': .24, 'grips': grip_report, 'carry': carry,
          'runtime_locomotion': 'Idle + ProductionToolComponent::UpdateTwoHandLocomotion, footstep phase',
          'runtime_tested': False, 'preview_rendered': False}
for clip, duration in CLIPS.items():
    name = 'A_RusticPickaxe_' + clip
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    rig.animation_data.action = action
    scene.render.fps = FPS
    scene.render.fps_base = 1
    scene.frame_start = 0
    scene.frame_end = round(duration * FPS)
    previous = {}
    for frame in range(scene.frame_end + 1):
        scene.frame_set(frame)
        time = frame / FPS
        wpn = idle[frame] if clip == 'Idle' else equip[frame] if clip == 'Equip' else \
            mining_frame(clip, frame, time) if clip in mining else ready
        pose = {name: matrix.copy() for name, matrix in rest.items()}
        for side in ('l', 'r'):
            solve_arm(pose, side, wpn @ grips[side])
        pose['WPN_root'] = wpn.copy()
        if clip in carry:
            # Baked editable reference of the component-space movement. Runtime
            # takes this phase from footsteps and fades motion in/out continuously.
            travel = Vector(carry[clip]['travel_cm']) * .01
            pitch, yaw, roll = [math.radians(v) for v in carry[clip]['angles_degrees']]
            phase = 2*math.pi*time/duration
            offset = Vector((travel.y*math.cos(phase), travel.x*math.sin(2*phase),
                -travel.z*(math.cos(2*phase)+.12*math.cos(4*phase))/1.12))
            rotation = Matrix.Rotation(pitch*math.sin(2*phase-.25), 4, 'X') @ \
                Matrix.Rotation(roll*math.cos(phase-.18), 4, 'Y') @ \
                Matrix.Rotation(yaw*math.sin(phase-.3), 4, 'Z')
            center = (pose['hand_l'].translation + pose['hand_r'].translation)*.5
            transform = Matrix.Translation(center+offset) @ rotation @ Matrix.Translation(-center)
            pose = {name: transform @ matrix for name, matrix in pose.items()}
        for bone in rig.pose.bones:
            parent_inverse = pose[bone.parent.name].inverted() if bone.parent else Matrix.Identity(4)
            bone.matrix_basis = local_rest[bone.name].inverted() @ parent_inverse @ pose[bone.name]
        for bone in rig.pose.bones:
            bone.rotation_mode = 'QUATERNION'
            q = bone.rotation_quaternion.copy()
            if bone.name in previous and q.dot(previous[bone.name]) < 0:
                q.negate()
            bone.rotation_quaternion = q
            previous[bone.name] = q.copy()
            for channel in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(channel, frame=frame, group=bone.name)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'
    export(name, [rig], True)
    print('PICKAXE_TWO_HAND_EXPORTED', clip, flush=True)

action_on(rig, 'A_RusticPickaxe_Idle')
scene.frame_end = 450
scene.frame_set(0)
# Use the real extracted maps in the editable file, not FBX-created missing paths.
material = tool.data.materials[0]
material.use_nodes = True
nodes, links = material.node_tree.nodes, material.node_tree.links
nodes.clear()
output = nodes.new('ShaderNodeOutputMaterial')
shader = nodes.new('ShaderNodeBsdfPrincipled')
links.new(shader.outputs['BSDF'], output.inputs['Surface'])
images = {}
for label, color_space in (('BaseColor', 'sRGB'), ('MetallicRoughness', 'Non-Color'), ('Normal', 'Non-Color')):
    texture = nodes.new('ShaderNodeTexImage')
    texture.image = bpy.data.images.load(str(HERE/'Textures'/(label+'.jpg')), check_existing=False)
    texture.image.colorspace_settings.name = color_space
    texture.image.pack()
    images[label] = texture
links.new(images['BaseColor'].outputs['Color'], shader.inputs['Base Color'])
channels = nodes.new('ShaderNodeSeparateColor')
links.new(images['MetallicRoughness'].outputs['Color'], channels.inputs['Color'])
links.new(channels.outputs['Green'], shader.inputs['Roughness'])
links.new(channels.outputs['Blue'], shader.inputs['Metallic'])
normal = nodes.new('ShaderNodeNormalMap')
links.new(images['Normal'].outputs['Color'], normal.inputs['Color'])
links.new(normal.outputs['Normal'], shader.inputs['Normal'])
blend = HERE / 'RusticPickaxe_TwoHand_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
report['blend'] = str(blend)
(HERE / 'authoring.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('RUSTIC_PICKAXE_AUTHORED', flush=True)
