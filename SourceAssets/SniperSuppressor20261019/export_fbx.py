import bpy
from mathutils import Matrix
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'SniperHeavySuppressor_Editable.blend'))
bpy.ops.object.select_all(action='DESELECT');ob=bpy.data.objects['SM_SniperHeavySuppressor'];ob.select_set(True);bpy.context.view_layer.objects.active=ob
# Export actual centimetre vertices. Legacy FBX reimports can retain their
# previous import scale even when a new ImportUI requests a different value.
ob.data.transform(Matrix.Scale(100.,4));bpy.context.scene.unit_settings.scale_length=.01
bpy.ops.export_scene.fbx(filepath=str(O/'Exports/SM_SniperHeavySuppressor.fbx'),use_selection=True,object_types={'MESH'},global_scale=1.,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Y',axis_up='Z',use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,bake_anim=False)
print('SNIPER_SUPPRESSOR_FBX_EXPORTED',flush=True)
