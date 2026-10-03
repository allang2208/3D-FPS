"""Restore the coherent source wrist rotations for landing only; retain approved air clips."""
import bpy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
PROJECT = ROOT.parents[2]
CLEAN = ROOT.parent / 'pounce_arm_refine'
APPROVED = ROOT.parent / 'pounce_forward_flip_v3_20261002'
ROLE = 'PounceLand'
HANDS = ('LeftHand', 'RightHand')
contract = json.loads((CLEAN / 'animation_contract.json').read_text(encoding='utf-8'))
count = contract['clips'][ROLE]['frames'][1] + 1
target_file = PROJECT / 'Content/Monsters/Mutant3Meshy/KhaimeraV2/Animations/A_Mutant3_PounceLand.uasset'
source_hash = hashlib.sha256(target_file.read_bytes()).hexdigest()

def activate(rig, action):
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]
    for track in rig.animation_data.nla_tracks:
        track.mute = True

# Use the source wrist rotations already coordinated with these exact landing
# shoulder, elbow and forearm poses. Do not unwind the V2 downward constraint and
# V3 180-degree turn as two independent moving rotations during ground contact.
bpy.ops.wm.open_mainfile(filepath=str(CLEAN / 'Mutant3_Pounce_ReferenceRake.blend'))
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
activate(rig, bpy.data.actions['A_Mutant3_' + ROLE])
poses = []
for frame in range(count):
    bpy.context.scene.frame_set(frame)
    poses.append({name: rig.pose.bones[name].rotation_quaternion.copy() for name in HANDS})

# Keep the accepted windup/flight actions and the existing landing finger shape
# in the editable source. Only the landing wrists receive new keys.
bpy.ops.wm.open_mainfile(filepath=str(APPROVED / 'Mutant3_Pounce_ForwardFlipV3.blend'))
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
original = bpy.data.actions['A_Mutant3_' + ROLE]
original.name = 'RejectedLandingWristsV3_' + original.name
action = original.copy()
action.name = 'A_Mutant3_' + ROLE
action.use_fake_user = True
activate(rig, action)
scene = bpy.context.scene
scene.render.fps, scene.render.fps_base = 60, 1
scene.frame_start, scene.frame_end = contract['clips'][ROLE]['frames']
previous = {}
for frame, pose in enumerate(poses):
    scene.frame_set(frame)
    for name in HANDS:
        rotation = pose[name].normalized()
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
output = ROOT / 'animations'
output.mkdir(exist_ok=True)
bpy.ops.export_scene.fbx(
    filepath=str(output / (action.name + '.fbx')), use_selection=True,
    object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False, use_armature_deform_only=False,
    bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
    bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0,
    axis_forward='-Y', axis_up='Z', apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
    mesh_smooth_type='FACE', path_mode='AUTO', embed_textures=False)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'Mutant3_Pounce_LandingWristV4.blend'))
result = {
    'revision': 'LandingWristV4_20261002',
    'state': 'Landing wrist source exported; production installation pending',
    'source': str(CLEAN / 'Mutant3_Pounce_ReferenceRake.blend'),
    'approved_air_source': str(APPROVED / 'Mutant3_Pounce_ForwardFlipV3.blend'),
    'source_license': 'Existing licensed Khaimera animation and Meshy character; local binary sources only',
    'clips': {ROLE: contract['clips'][ROLE]},
    'source_sha256': {ROLE: source_hash},
    'changed_rotation_tracks': {ROLE: list(HANDS)},
    'landing_wrist': 'Original coherent source local wrist rotations from first landing frame; no downward plane constraint or 180-degree turn',
    'handoff': 'Existing runtime upper-body snapshot blend over 0.14 seconds; no new instant wrist override',
    'preserved': 'Windup and flight packages untouched; landing fingers, body and all translation/scale keys untouched',
    'user_feedback': 'V3 windup and airborne direction accepted; V3 landing wrists rejected',
    'runtime_tested': False,
    'visual_tested': False,
}
(ROOT / 'animation_contract.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('POUNCE_LANDING_WRIST_AUTHORED: landing only, two wrist rotation tracks', flush=True)
