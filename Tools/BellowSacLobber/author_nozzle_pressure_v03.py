"""Add a radial pressure wave to the saved V02 lob, preserving other tracks."""
import json
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BellowSacLobberMeshy20261012')
OUT = ROOT / 'NozzleV03'
OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'CombatV02/BellowSacLobber_attack_v02.blend'))
scene = bpy.context.scene
rig = next(obj for obj in scene.objects if obj.type == 'ARMATURE')
mesh_objects = [obj for obj in scene.objects if obj.type == 'MESH' and any(
    modifier.type == 'ARMATURE' and modifier.object == rig for modifier in obj.modifiers)]
source = bpy.data.actions['A_BellowSacLobber_Lob_v02']
nozzle = ('Bone_031', 'Bone_030', 'Bone_029', 'Bone_028')
strengths = (.16, .19, .22, .20)
rest = {bone.name: bone.matrix_local.copy() for bone in rig.data.bones}
scene.render.fps = 60
scene.render.fps_base = 1.
scene.frame_start = 1
scene.frame_end = 133


def curve(t, keys):
    for (start, a), (end, b) in zip(keys, keys[1:]):
        if t <= end:
            x = max(0., min(1., (t - start) / (end - start)))
            return a + (b - a) * x**3 * (6*x*x - 15*x + 10)
    return keys[-1][1]


def pressure_keys(index):
    # Small early pulse, sustained loading, then root-to-tip release at 1.2 s.
    delay = .065 * index
    return [(0., 0.), (.16 + delay, 0.), (.57 + delay, .55),
            (.74 + delay, .30), (1.055 + .028*index, 1.),
            (1.13 + .023*index, 1.), (1.27 + .015*index, -.25),
            (1.48 + .015*index, .14), (1.84 + .015*index, 0.), (2.2, 0.)]


# Read the existing baked action before editing its copy. This keeps body,
# sac, feet and nozzle aiming on their original clock and poses.
rig.animation_data.action = source
samples = []
for frame in range(1, 134):
    scene.frame_set(frame)
    samples.append({name: rig.pose.bones[name].matrix.copy()
                    for name in (*nozzle, 'Bone_002')})

action = source.copy()
action.name = 'A_BellowSacLobber_Lob_Pressure_v03'
action.use_fake_user = True
rig.animation_data.action = action
for frame, base in enumerate(samples, 1):
    scene.frame_set(frame)
    t = (frame - 1) / 60.
    desired = {'Bone_002': base['Bone_002']}
    for index, name in enumerate(nozzle):
        mat = base[name]
        radius = 1. + strengths[index] * curve(t, pressure_keys(index))
        # Bone Y runs along the tube. Independent component-space radii avoid
        # multiplying inflation down the chain or stretching the firing tube.
        desired[name] = Matrix.LocRotScale(mat.translation, mat.to_quaternion(),
                                          Vector((radius, 1., radius)))
    for name in nozzle:
        bone = rig.pose.bones[name]
        parent = bone.parent.name
        bone.matrix_basis = (rest[name].inverted() @ rest[parent]
                             @ desired[parent].inverted() @ desired[name])
        for prop in ('location', 'rotation_quaternion', 'scale'):
            bone.keyframe_insert(data_path=prop, frame=frame, group=name)
    bpy.context.view_layer.update()

for obj in scene.objects:
    obj.select_set(False)
rig.select_set(True)
for obj in mesh_objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = rig
fbx_path = OUT / 'A_BellowSacLobber_Lob_Pressure_v03.fbx'
bpy.ops.export_scene.fbx(
    filepath=str(fbx_path), use_selection=True, object_types={'ARMATURE', 'MESH'},
    add_leaf_bones=False, use_armature_deform_only=True, axis_forward='-Y', axis_up='Z',
    apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE',
    use_mesh_modifiers=False, bake_anim=True, bake_anim_use_nla_strips=False,
    bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True,
    bake_anim_simplify_factor=0.)
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'BellowSacLobber_nozzle_pressure_v03.blend'))
record = {
    'fbx': str(fbx_path), 'source_action': source.name, 'action': action.name,
    'duration_seconds': 2.2, 'fps': 60, 'target_lock_seconds': .85, 'release_seconds': 1.2,
    'nozzle_segments_root_to_tip': [
        {'bone': name, 'peak_radial_expansion': strengths[index],
         'pressure_keys_seconds': pressure_keys(index)} for index, name in enumerate(nozzle)],
    'model_skin_and_other_animation_tracks': 'unchanged V02',
    'runtime_tested': False, 'rendered': False}
(OUT / 'nozzle_manifest_v03.json').write_text(
    json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print('BELLOW_NOZZLE_V03_AUTHORED ' + str(fbx_path), flush=True)
