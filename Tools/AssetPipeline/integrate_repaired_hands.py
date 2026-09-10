"""Combine a reviewed hands-only repair with the unchanged supplied AKM/rig."""
import argparse, bpy, json, sys
from pathlib import Path
from mathutils import Matrix

parser = argparse.ArgumentParser()
parser.add_argument('--hands-blend', required=True)
parser.add_argument('--mesh-name', default='SK_ArmsReplacement_WRAD')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
root = Path(r'D:/FPS3D/FPSGAME')
out = root / 'SourceAssets/ArmsRepair20260909/Integrated'
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(root / 'SourceAssets/AKMReplacement/SK_AKM_Replacement_Source.blend'))
rig = bpy.data.objects['SK_AKM_Viewmodel']
bone_matrices = {b.name: b.matrix_local.copy() for b in rig.data.bones}
for obj in list(bpy.data.objects):
    if obj.type == 'MESH' and obj.parent == rig and obj.name.startswith('SK_ArmsReplacement'):
        bpy.data.objects.remove(obj, do_unlink=True)
with bpy.data.libraries.load(str(Path(args.hands_blend).resolve()), link=False) as (available, imported):
    assert args.mesh_name in available.objects, args.mesh_name
    imported.objects = [args.mesh_name]
mesh = imported.objects[0]
bpy.context.collection.objects.link(mesh)
mesh.parent = rig
mesh.matrix_parent_inverse = Matrix.Identity(4)
mesh.matrix_basis = Matrix.Identity(4)
for modifier in mesh.modifiers:
    if modifier.type == 'ARMATURE':
        modifier.object = rig
        assert not modifier.use_deform_preserve_volume, 'UE LBS validation requires linear skinning'
mesh.hide_render = False
mesh.hide_set(False)
for i, material in enumerate(mesh.data.materials):
    if material and material.name.startswith('M_ArmsReplacement_'):
        base = material.name.split('.')[0]
        if base in bpy.data.materials:
            mesh.data.materials[i] = bpy.data.materials[base]
assert set(bone_matrices) == set(rig.data.bones.keys())
assert all(max(abs(v) for row in (rig.data.bones[n].matrix_local - before) for v in row) < 1e-8
           for n, before in bone_matrices.items())
action = bpy.data.actions['AKM_idle']
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene = bpy.context.scene
scene.render.fps = 24
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'SK_AKM_HandsRepair_Source.blend'))
meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.parent == rig and not obj.hide_render]
bpy.ops.object.select_all(action='DESELECT')
rig.hide_set(False)
rig.select_set(True)
for obj in meshes:
    obj.hide_set(False)
    obj.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(filepath=str(out / 'SK_AKM_HandsRepair.fbx'), use_selection=True,
    object_types={'ARMATURE','MESH'}, apply_scale_options='FBX_SCALE_ALL', apply_unit_scale=True,
    use_space_transform=True, axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
    use_armature_deform_only=False, bake_anim=False, path_mode='COPY', embed_textures=True,
    mesh_smooth_type='FACE', use_tspace=True)
report = {'hands_source': str(Path(args.hands_blend).resolve()), 'mesh': mesh.name,
          'bone_count': len(bone_matrices), 'bind_matrices_unchanged': True,
          'linear_skinning': True, 'exported_meshes': [obj.name for obj in meshes],
          'animation_assets_changed': False}
(out / 'integration.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print('HANDS_REPAIR_INTEGRATION_OK', json.dumps(report))
