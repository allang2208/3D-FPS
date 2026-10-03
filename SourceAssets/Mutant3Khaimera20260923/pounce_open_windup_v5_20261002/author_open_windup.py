"""Bake an open, forward windup arm path, retaining the approved takeoff endpoint."""
import bpy
import hashlib
import json
import math
from pathlib import Path
from mathutils import Quaternion, Vector

ROOT = Path(__file__).parent
PROJECT = ROOT.parents[2]
SOURCE = ROOT.parent / 'pounce_landing_wrist_v4_20261002'
ROLE = 'PounceWindup'
SIDES = ('Left', 'Right')
NAMES = [side + suffix for side in SIDES for suffix in ('Arm', 'ForeArm', 'Hand')]
SOURCE_BLEND = SOURCE / 'Mutant3_Pounce_LandingWristV4.blend'
clip = {'source': 'RMB_60fps', 'seconds': .60, 'fps': 60, 'loop': False, 'frames': [0, 36]}
target_file = PROJECT / 'Content/Monsters/Mutant3Meshy/KhaimeraV2/Animations/A_Mutant3_PounceWindup.uasset'
source_hash = hashlib.sha256(target_file.read_bytes()).hexdigest()

bpy.ops.wm.open_mainfile(filepath=str(SOURCE_BLEND))
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
scene = bpy.context.scene
scene.render.fps, scene.render.fps_base = 60, 1
original = bpy.data.actions['A_Mutant3_' + ROLE]
rig.animation_data.action = original
if original.slots:
    rig.animation_data.action_slot = original.slots[0]
for track in rig.animation_data.nla_tracks:
    track.mute = True

def smooth(start, end, time):
    value = max(0., min(1., (time - start) / (end - start)))
    return value * value * (3. - 2. * value)

def body_frame():
    lateral = rig.pose.bones['LeftArm'].head - rig.pose.bones['RightArm'].head
    lateral.z = 0.
    lateral.normalize()
    up = Vector((0., 0., 1.))
    forward = lateral.cross(up).normalized()
    return lateral, forward, up

def to_frame(vector, axes):
    return Vector(tuple(vector.dot(axis) for axis in axes))

def from_frame(vector, axes):
    return axes[0] * vector.x + axes[1] * vector.y + axes[2] * vector.z

baseline = []
for frame in range(37):
    scene.frame_set(frame)
    baseline.append({name: rig.pose.bones[name].rotation_quaternion.copy() for name in NAMES})
scene.frame_set(36)
end_axes = body_frame()
end = {}
for side in SIDES:
    shoulder = rig.pose.bones[side + 'Arm'].head.copy()
    elbow = rig.pose.bones[side + 'ForeArm'].head.copy()
    wrist = rig.pose.bones[side + 'Hand'].head.copy()
    end[side] = {'wrist_offset': to_frame(wrist - shoulder, end_axes),
                 'elbow_offset': to_frame(elbow - shoulder, end_axes),
                 'hand_rotation': baseline[36][side + 'Hand'].copy()}

def swing_bone(name, delta):
    bone = rig.pose.bones[name]
    pose_rotation = bone.matrix.to_quaternion()
    local_delta = pose_rotation.inverted() @ delta @ pose_rotation
    bone.rotation_quaternion = (bone.rotation_quaternion @ local_delta).normalized()
    bpy.context.view_layer.update()

poses = []
for frame in range(37):
    scene.frame_set(frame)
    for name in NAMES:
        rig.pose.bones[name].rotation_quaternion = baseline[frame][name]
    bpy.context.view_layer.update()
    # Preserve the complete takeoff endpoint verbatim, including forearm twist.
    if frame == 36:
        poses.append({name: baseline[frame][name].copy() for name in NAMES})
        continue
    time = frame / 60.
    axes = body_frame()
    lateral, forward, up = axes
    coil = smooth(0., .22, time)
    raise_hands = smooth(.28, .54, time)
    rejoin = smooth(.50, .60, time)
    hand_turn = smooth(.20, .54, time)
    for side, sign in (('Left', 1.), ('Right', -1.)):
        arm_name, forearm_name, hand_name = (side + suffix for suffix in ('Arm', 'ForeArm', 'Hand'))
        shoulder = rig.pose.bones[arm_name].head.copy()
        original_elbow = rig.pose.bones[forearm_name].head.copy()
        original_wrist = rig.pose.bones[hand_name].head.copy()
        upper_length = (original_elbow - shoulder).length
        lower_length = (original_wrist - original_elbow).length
        reach = upper_length + lower_length

        # Keep each hand outside its own shoulder line, in front of the chest.
        # The elbow bends outward and down instead of crossing the torso.
        ready_offset = (lateral * sign * (.22 * reach)
                        + forward * ((.40 + .10 * coil) * reach)
                        - up * ((.28 - .12 * coil) * reach))
        launch_offset = from_frame(end[side]['wrist_offset'], axes)
        target = shoulder + ready_offset.lerp(launch_offset, raise_hands)
        target = target.lerp(original_wrist, rejoin)
        ready_pole = lateral * sign * (.50 * reach) - up * (.34 * reach) - forward * (.04 * reach)
        launch_pole = from_frame(end[side]['elbow_offset'], axes)
        pole = ready_pole.lerp(launch_pole, raise_hands).lerp(original_elbow - shoulder, rejoin)

        # Analytic two-bone positioning changes rotations only. The pole and
        # target belong to one arm solution; no independent wrist-facing lock.
        direction = target - shoulder
        distance = max(abs(upper_length - lower_length) + .001 * reach,
                       min(direction.length, .995 * reach))
        direction.normalize()
        target = shoulder + direction * distance
        bend_direction = pole - direction * pole.dot(direction)
        bend_direction.normalize()
        along = (upper_length * upper_length + distance * distance - lower_length * lower_length) / (2. * distance)
        height = math.sqrt(max(0., upper_length * upper_length - along * along))
        elbow = shoulder + direction * along + bend_direction * height
        upper_direction = (elbow - shoulder).normalized()
        arm_swing = (original_elbow - shoulder).rotation_difference(elbow - shoulder)
        original_plane = (original_elbow - shoulder).cross(original_wrist - original_elbow).normalized()
        desired_plane = (elbow - shoulder).cross(target - elbow).normalized()
        swung_plane = arm_swing @ original_plane
        plane_turn = math.atan2(upper_direction.dot(swung_plane.cross(desired_plane)),
                               max(-1., min(1., swung_plane.dot(desired_plane))))
        # Transport the original elbow hinge plane with the upper arm. The
        # forearm then bends within that plane instead of supplying axial twist
        # to compensate for an independently swung shoulder.
        swing_bone(arm_name, Quaternion(upper_direction, plane_turn) @ arm_swing)
        forearm_head = rig.pose.bones[forearm_name].head.copy()
        wrist_head = rig.pose.bones[hand_name].head.copy()
        swing_bone(forearm_name, (wrist_head - forearm_head).rotation_difference(target - forearm_head))

        # Early windup uses the neutral bind wrist. A single shortest quaternion
        # path prepares the approved launch wrist while the hands are separated.
        rig.pose.bones[hand_name].rotation_quaternion = Quaternion().slerp(
            end[side]['hand_rotation'], hand_turn).normalized()
        bpy.context.view_layer.update()
    poses.append({name: rig.pose.bones[name].rotation_quaternion.copy() for name in NAMES})

original.name = 'BeforeOpenWindupV5_' + original.name
action = original.copy()
action.name = 'A_Mutant3_' + ROLE
action.use_fake_user = True
rig.animation_data.action = action
if action.slots:
    rig.animation_data.action_slot = action.slots[0]
scene.frame_start, scene.frame_end = 0, 36
previous = {}
for frame, pose in enumerate(poses):
    scene.frame_set(frame)
    for name in NAMES:
        rotation = pose[name].copy()
        if name in previous and rotation.dot(previous[name]) < 0:
            rotation.negate()
        bone = rig.pose.bones[name]
        bone.rotation_mode = 'QUATERNION'
        bone.rotation_quaternion = rotation
        bone.keyframe_insert('rotation_quaternion', frame=frame, group=name)
        previous[name] = rotation.copy()
paths = {f'pose.bones["{name}"].rotation_quaternion' for name in NAMES}
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                if curve.data_path in paths:
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'
scene.frame_set(0)
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
for obj in bpy.data.objects:
    if obj.type == 'MESH' and any(mod.type == 'ARMATURE' and mod.object == rig for mod in obj.modifiers):
        obj.select_set(True)
bpy.context.view_layer.objects.active = rig
output = ROOT / 'animations'
output.mkdir(exist_ok=True)
bpy.ops.export_scene.fbx(
    filepath=str(output / (action.name + '.fbx')), use_selection=True,
    object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False, use_armature_deform_only=False,
    bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
    bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0,
    axis_forward='-Y', axis_up='Z', apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
    mesh_smooth_type='FACE', path_mode='AUTO', embed_textures=False)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'Mutant3_Pounce_OpenWindupV5.blend'))
result = {
    'revision': 'OpenWindupV5_20261002',
    'state': 'Open windup source exported; production installation pending',
    'source': str(SOURCE_BLEND),
    'source_license': 'Existing licensed Khaimera animation and Meshy character; local binary sources only',
    'clips': {ROLE: clip},
    'source_sha256': {ROLE: source_hash},
    'changed_rotation_tracks': {ROLE: NAMES},
    'design': 'Hands separated in front of own shoulders; elbows outward/down; hands lift forward/up to the approved takeoff pose',
    'coil_seconds': [0., .22],
    'raise_seconds': [.28, .54],
    'wrist_turn_seconds': [.20, .54],
    'rejoin_source_seconds': [.50, .60],
    'last_frame': 'Original approved V3 local arm, forearm and hand rotations copied verbatim',
    'preserved': 'Flight and landing packages untouched; windup clavicles, torso, crouch, feet, fingers and all translation/scale tracks untouched',
    'runtime_tested': False,
    'visual_tested': False,
}
(ROOT / 'animation_contract.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('POUNCE_OPEN_WINDUP_AUTHORED: windup only, six arm rotation tracks', flush=True)
