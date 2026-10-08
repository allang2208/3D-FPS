"""Keep the thin right lining on its fitted surface, with two-sided fabric shading."""
from pathlib import Path
import bpy
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/RigRepairV3')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'BoundCongregate_RigV3.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis.identity()
bpy.context.view_layer.update()
ob=bpy.data.objects['BC_RightLining'];proxy=bpy.data.objects[ob.name+'_SimulationProxy']
mat=ob.data.materials[0];ob.data=proxy.data.copy();ob.data.materials[0]=mat;bpy.context.view_layer.objects.active=ob
# A loose thin lining uses the fitted single surface. Offset shells around its
# sharp torn folds can enter flesh even when the simulation surface is clear.
# The existing UE/Blender fabric material renders both sides.
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'BoundCongregate_RigV3.blend'))
bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.context.scene.objects:
    if ob.type in ('MESH','ARMATURE'):ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(ROOT/'SK_BoundCongregate_RigV3.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,
    use_armature_deform_only=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
print('FITTED_THIN_LINING_SAVED',flush=True)
