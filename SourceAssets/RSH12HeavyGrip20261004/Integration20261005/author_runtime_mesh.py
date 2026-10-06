"""Use the authored physical rubber UV as UE tangent UV0 on the runtime copy."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent;source=O.parent
bpy.ops.wm.open_mainfile(filepath=str(source/'RSH12_HeavyGrip_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
ob=bpy.data.objects['SM_RSH12_HeavyGrip']
for collection in ob.users_collection:collection.hide_viewport=False
ob.hide_set(False);ob.hide_viewport=False
uv0=ob.data.uv_layers[0];uv1=ob.data.uv_layers[1]
for face in ob.data.polygons:
    if ob.data.materials[face.material_index].name=='RSH12HeavyGrip_RubberContactShell':
        for li in face.loop_indices:uv0.data[li].uv=uv1.data[li].uv
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
bpy.ops.export_scene.fbx(filepath=str(O/'SM_RSH12_HeavyGrip.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='RELATIVE')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'RSH12_HeavyGrip_RuntimeUV.blend'))
print('RSH_HEAVY_RUNTIME_MESH_AUTHORED',flush=True)
