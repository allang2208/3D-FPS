"""Re-export the saved authored actions with complete FBX reference poses."""
import bpy, sys
from pathlib import Path
from mathutils import Matrix

O=Path(__file__).parent
sys.path.insert(0,str(O))
from fbx_bind_pose import install
install()
bpy.context.preferences.filepaths.save_version=0
try:
    bpy.ops.wm.open_mainfile(filepath=str(O/'DanWesson715_Manny_Editable.blend'))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error) or 'SK_DW715_Manny' not in bpy.data.objects:raise
rig=bpy.data.objects['SK_DW715_Manny'];scene=bpy.context.scene
actions={a.name[6:]:a for a in bpy.data.actions if a.name.startswith('DW715_')}
for kind,action in actions.items():
    rig.animation_data_create();rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    scene.frame_start=0;scene.frame_end=round(action.frame_range[1]);scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(O/'Animations'/f'A_DW715_{kind}.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_step=.5,bake_anim_simplify_factor=0)
    print('DW715_EXPORTED_COMPLETE_POSE',kind,flush=True)
rig.animation_data_clear()
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT')
for obj in scene.objects:
    if obj==rig or obj.type=='MESH':obj.hide_set(False);obj.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(O/'SK_DW715_Manny.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
print('DW715_COMPLETE_POSE_EXPORT_FINISHED',flush=True)
