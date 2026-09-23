"""Export the accepted claw mesh with explicit source/body and refreshed finger normals.
No vertex, UV, skin, bone or animation edits; no preview render.
"""
import bpy
import json
from pathlib import Path
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'Mutant3Khaimera20260923/claw_reference_20260923/Mutant3_OpenClaw_Source.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
mesh = bpy.data.objects['Mesh0']
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
rig.animation_data_clear()
for bone in rig.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
data = mesh.data
source_normals = [n.vector.copy() for n in data.corner_normals]
custom_before = data.has_custom_normals
finger_groups = {g.index for g in mesh.vertex_groups if g.name.endswith('_Claw')}
finger_weight = [min(1.0, sum(g.weight for g in v.groups if g.group in finger_groups)) for v in data.vertices]
# Zero custom vectors request Blender's smooth geometric normals. Only the
# reshaped fingers receive these; body normals keep the original bake basis.
for polygon in data.polygons:
    polygon.use_smooth = True
data.normals_split_custom_set([(0.0, 0.0, 0.0)] * len(data.loops))
data.update()
fresh_normals = [n.vector.copy() for n in data.corner_normals]
normals = []
for loop, old, fresh in zip(data.loops, source_normals, fresh_normals):
    weight = finger_weight[loop.vertex_index]
    normal = old.lerp(fresh, weight).normalized()
    normals.append(tuple(normal))
data.normals_split_custom_set(normals)
data.update()
bpy.ops.object.select_all(action='DESELECT')
mesh.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Mutant3_SurfacePolish.blend'))
bpy.ops.export_scene.fbx(filepath=str(ROOT/'SK_Mutant3_Claw.fbx'), use_selection=True,
    object_types={'ARMATURE','MESH'}, add_leaf_bones=False, use_armature_deform_only=False,
    bake_anim=False, axis_forward='-Y', axis_up='Z', apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE', path_mode='STRIP')
report={'source':str(SOURCE),'mesh_fbx':str(ROOT/'SK_Mutant3_Claw.fbx'),
    'vertices':len(data.vertices),'polygons':len(data.polygons),'source_custom_normals':custom_before,
    'normal_policy':'source corner normals on body; smooth geometric normals blended on claw-weighted fingers',
    'finger_vertices':sum(w>0 for w in finger_weight),
    'positions_uv_weights_bones_animations_edited':False,'preview_rendered':False}
(ROOT/'normal_authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('MUTANT3_NORMALS_AUTHORED '+json.dumps(report),flush=True)
