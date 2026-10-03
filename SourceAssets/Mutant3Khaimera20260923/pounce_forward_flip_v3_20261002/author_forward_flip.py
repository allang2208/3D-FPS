"""Reverse the rejected hands around each palm's transverse axis, before takeoff."""
import bpy
import hashlib
import json
import math
from pathlib import Path
from mathutils import Quaternion, Vector

ROOT = Path(__file__).parent
PROJECT = ROOT.parents[2]
SOURCE = ROOT.parent / 'pounce_takeoff_hands_v2_20261002'
ROLES = ('PounceWindup', 'PounceFlight', 'PounceLand')
HANDS = ('LeftHand', 'RightHand')
SOURCE_BLEND = SOURCE / 'Mutant3_Pounce_TakeoffHandsV2.blend'
contract = json.loads((SOURCE / 'animation_contract.json').read_text(encoding='utf-8'))
basis = json.loads((SOURCE / 'authoring_basis.json').read_text(encoding='utf-8'))['basis']
source_hashes = {}
for role in ROLES:
    path = PROJECT / 'Content/Monsters/Mutant3Meshy/KhaimeraV2/Animations' / (
        'A_Mutant3_' + role + '.uasset')
    source_hashes[role] = hashlib.sha256(path.read_bytes()).hexdigest()

bpy.ops.wm.open_mainfile(filepath=str(SOURCE_BLEND))
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
    value = max(0., min(1., (time - start) / (end - start)))
    return value * value * (3 - 2 * value)

def turn_weight(role, time):
    if role == 'PounceWindup':
        return smooth(.08, .38, time)
    if role == 'PounceFlight':
        return 1.
    return 1. - smooth(.16, .64, time)

# A roll about the wrist-to-finger axis would leave the inward-pointing hand
# direction intact. Turn about the cross-palm axis instead: at 180 degrees both
# the palm normal and the wrist-to-finger direction reverse. Positive rotation
# takes the fingers over the palm's opposite normal during the windup.
axes = {}
for side in ('Left', 'Right'):
    normal = Vector(basis[side]['palm_normal_local']).normalized()
    longitudinal = Vector(basis[side]['long_axis_local']).normalized()
    axes[side + 'Hand'] = normal.cross(longitudinal).normalized()

output = ROOT / 'animations'
output.mkdir(exist_ok=True)
for role in ROLES:
    original = originals[role]
    activate(original)
    scene.frame_start, scene.frame_end = contract['clips'][role]['frames']
    baseline = []
    for frame in range(scene.frame_end + 1):
        scene.frame_set(frame)
        baseline.append({name: rig.pose.bones[name].rotation_quaternion.copy() for name in HANDS})
    original.name = 'RejectedTakeoffHandsV2_' + original.name
    action = original.copy()
    action.name = 'A_Mutant3_' + role
    action.use_fake_user = True
    activate(action)
    previous = {}
    for frame, pose in enumerate(baseline):
        scene.frame_set(frame)
        weight = turn_weight(role, frame / 60.)
        for name in HANDS:
            rotation = (pose[name] @ Quaternion(axes[name], math.pi * weight)).normalized()
            if name in previous and rotation.dot(previous[name]) < 0:
                rotation.negate()
            bone = rig.pose.bones[name]
            bone.rotation_mode = 'QUATERNION'
            bone.rotation_quaternion = rotation
            bone.keyframe_insert('rotation_quaternion', frame=frame, group=name)
            previous[name] = rotation.copy()
    paths = {f'pose.bones["{name}"].rotation_quaternion' for name in HANDS}
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
        filepath=str(output / (action.name + '.fbx')), use_selection=True,
        object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False, use_armature_deform_only=False,
        bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0,
        axis_forward='-Y', axis_up='Z', apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
        mesh_smooth_type='FACE', path_mode='AUTO', embed_textures=False)
    print('POUNCE_FORWARD_FLIP_EXPORTED ' + role, flush=True)

bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'Mutant3_Pounce_ForwardFlipV3.blend'))
result = {
    'revision': 'ForwardFlipV3_20261002',
    'state': 'Source authored; production installation pending',
    'source': str(SOURCE_BLEND),
    'user_reference': 'C:/Users/allan/AppData/Local/Temp/codex-clipboard-f49418bd-3048-492e-8bef-1b8c6f692a3a.png',
    'source_license': contract['source_license'],
    'clips': {role: contract['clips'][role] for role in ROLES},
    'source_sha256': source_hashes,
    'changed_rotation_tracks': {role: list(HANDS) for role in ROLES},
    'hand_flip_degrees': 180.,
    'hand_flip_axis_local': {name: list(axis) for name, axis in axes.items()},
    'design': 'Reverse the palm AND wrist-to-finger direction relative to rejected V2; forward clawing intent',
    'windup_turn_seconds': [.08, .38],
    'takeoff_seconds': .60,
    'flight_turn_weight': 1.,
    'land_release_seconds': [.16, .64],
    'finger_changes': 'None; preserve V2 local finger rotations and spread',
    'preserved': 'All translations/scales and all rotation tracks except LeftHand/RightHand in actual production assets',
    'runtime_tested': False,
    'visual_tested': False,
}
(ROOT / 'animation_contract.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('POUNCE_FORWARD_FLIP_AUTHORED', flush=True)
