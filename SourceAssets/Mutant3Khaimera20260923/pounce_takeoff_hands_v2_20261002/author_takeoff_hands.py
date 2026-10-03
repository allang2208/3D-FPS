"""Prepare the complete downward claw before takeoff; preserve the original body."""
import bpy
import hashlib
import json
import math
from pathlib import Path
from mathutils import Quaternion, Vector

ROOT = Path(__file__).parent
PROJECT = ROOT.parents[2]
SOURCE = ROOT.parent / 'pounce_arm_refine'
DEST = '/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations'
ROLES = ('PounceWindup', 'PounceFlight', 'PounceLand')
SIDES = ('Left', 'Right')
DIGITS = ('Index', 'Middle', 'Ring', 'Pinky', 'Thumb')
HANDS = [side + 'Hand' for side in SIDES]
FINGERS = [f'{side}{digit}{joint}_Claw' for side in SIDES
           for digit in DIGITS for joint in range(1, 4)]
NAMES = HANDS + FINGERS
DOWN = Vector((0, 0, -1))

contract = json.loads((SOURCE / 'animation_contract.json').read_text(encoding='utf-8'))
basis = json.loads((ROOT / 'authoring_basis.json').read_text(encoding='utf-8'))['basis']
chains = json.loads((ROOT.parent / 'claw_reference_20260923' / 'claw_skin.json')
                    .read_text(encoding='utf-8'))['chains']
source_hashes = {}
for role in ROLES:
    relative = Path('Monsters/Mutant3Meshy/KhaimeraV2/Animations') / ('A_Mutant3_' + role + '.uasset')
    source_hashes[role] = hashlib.sha256((PROJECT / 'Content' / relative).read_bytes()).hexdigest()

bpy.ops.wm.open_mainfile(filepath=str(SOURCE / 'Mutant3_Pounce_ReferenceRake.blend'))
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
scene = bpy.context.scene
scene.render.fps, scene.render.fps_base = 60, 1
for track in rig.animation_data.nla_tracks:
    track.mute = True
originals = {role: bpy.data.actions['A_Mutant3_' + role] for role in ROLES}

def activate(action):
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]

def smooth(start, end, time):
    t = max(0., min(1., (time - start) / (end - start)))
    return t * t * (3 - 2 * t)

def palm_weight(role, time):
    if role == 'PounceWindup':
        return smooth(.08, .38, time)
    if role == 'PounceFlight':
        return 1.
    return 1 - smooth(.16, .64, time)

def rake_weight(role, time):
    if role == 'PounceWindup':
        return smooth(.08, .38, time)
    if role == 'PounceFlight':
        return 1.
    return 1 - smooth(.16, .64, time)

def wrist_pitch(role, time):
    if role == 'PounceWindup':
        return 0.
    if role == 'PounceFlight':
        return 18. * smooth(0., .18, time)
    return 18.

curl_axes = {}
for key, chain in chains.items():
    direction = (Vector(chain['knots_world'][-1]) - Vector(chain['knots_world'][0])).normalized()
    curl = Vector((0, .8, -.6)).normalized() if key.endswith('Thumb') else DOWN
    axis = direction.cross(curl).normalized()
    for name in chain['bones']:
        rest = (rig.matrix_world @ rig.data.bones[name].matrix_local).to_quaternion()
        curl_axes[name] = rest.inverted() @ axis

authored = {}
for role in ROLES:
    activate(originals[role])
    frames = contract['clips'][role]['frames'][1]
    baseline = []
    for frame in range(frames + 1):
        scene.frame_set(frame)
        baseline.append({name: rig.pose.bones[name].rotation_quaternion.copy() for name in NAMES})
    poses = []
    for frame in range(frames + 1):
        scene.frame_set(frame)
        time = frame / 60.
        amount = palm_weight(role, time)
        for name in NAMES:
            rig.pose.bones[name].rotation_quaternion = baseline[frame][name]
        bpy.context.view_layer.update()
        for side in SIDES:
            name = side + 'Hand'
            hand = rig.pose.bones[name]
            world = (rig.matrix_world @ hand.matrix).to_quaternion()
            palm = (world @ Vector(basis[side]['palm_normal_local'])).normalized()
            # The palm plane, rather than any fingertip direction, defines facing.
            # Minimal swing adds no free yaw or independently prescribed elbow.
            swing = palm.rotation_difference(DOWN)
            corrected_long = swing @ (world @ Vector(basis[side]['long_axis_local']))
            corrected_long.z = 0
            corrected_long.normalize()
            bend_axis = DOWN.cross(corrected_long).normalized()
            bend = Quaternion(bend_axis, -math.radians(wrist_pitch(role, time)))
            full_delta = bend @ swing
            delta = Quaternion().slerp(full_delta, amount)
            local_delta = world.inverted() @ delta @ world
            hand.rotation_quaternion = (baseline[frame][name] @ local_delta).normalized()
            for digit in DIGITS:
                extra = (1., 4., 3.) if digit == 'Thumb' else (3., 10., 6.)
                for joint, degrees in enumerate(extra, 1):
                    finger = f'{side}{digit}{joint}_Claw'
                    rig.pose.bones[finger].rotation_quaternion = (
                        baseline[frame][finger] @ Quaternion(
                            curl_axes[finger], math.radians(degrees) * rake_weight(role, time)))
        poses.append({name: rig.pose.bones[name].rotation_quaternion.copy() for name in NAMES})
    authored[role] = poses

out = ROOT / 'animations'
out.mkdir(exist_ok=True)
for role in ROLES:
    original = originals[role]
    original.name = 'BeforePalmDown_' + original.name
    action = original.copy()
    action.name = 'A_Mutant3_' + role
    action.use_fake_user = True
    activate(action)
    scene.frame_start, scene.frame_end = contract['clips'][role]['frames']
    changed = NAMES
    previous = {}
    for frame, pose in enumerate(authored[role]):
        scene.frame_set(frame)
        for name in changed:
            q = pose[name].copy()
            if name in previous and q.dot(previous[name]) < 0:
                q.negate()
            bone = rig.pose.bones[name]
            bone.rotation_mode = 'QUATERNION'
            bone.rotation_quaternion = q
            bone.keyframe_insert('rotation_quaternion', frame=frame, group=name)
            previous[name] = q.copy()
    paths = {f'pose.bones["{name}"].rotation_quaternion' for name in changed}
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
    bpy.ops.export_scene.fbx(
        filepath=str(out / (action.name + '.fbx')), use_selection=True,
        object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False, use_armature_deform_only=False,
        bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0,
        axis_forward='-Y', axis_up='Z', apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
        mesh_smooth_type='FACE', path_mode='AUTO', embed_textures=False)
    print('POUNCE_TAKEOFF_HANDS_EXPORTED ' + role, flush=True)

bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'Mutant3_Pounce_TakeoffHandsV2.blend'))
contract = {
    'revision': 'TakeoffHandsV2_20261002',
    'state': 'Source authored; production installation pending',
    'source': str(SOURCE / 'Mutant3_Pounce_ReferenceRake.blend'),
    'source_license': 'Existing licensed Khaimera animation and Meshy character; local binary sources only',
    'clips': {role: contract['clips'][role] for role in ROLES},
    'source_sha256': source_hashes,
    'changed_rotation_tracks': {role: NAMES for role in ROLES},
    'palm_basis': basis,
    'palm_facing': 'Palm normal down and complete claw already at takeoff; wrist presses from 0 to 18 degrees in first 0.18 seconds',
    'windup_palm_and_finger_ramp_seconds': [.08, .38],
    'prepared_before_takeoff_seconds': .22,
    'flight_downward_wrist_seconds': [0., .18],
    'flight_finger_shape': 'Complete from frame zero; no delayed curl',
    'land_wrist_degrees': 18.,
    'land_release_seconds': [.16, .64],
    'finger_extra_curl_degrees': [3, 10, 6],
    'thumb_extra_curl_degrees': [1, 4, 3],
    'preserved': 'All translations/scales and all non-hand rotation tracks in the actual production assets',
    'runtime_tested': False,
    'visual_tested': False,
}
(ROOT / 'animation_contract.json').write_text(json.dumps(contract, indent=2), encoding='utf-8')
print('POUNCE_TAKEOFF_HANDS_AUTHORED', flush=True)
