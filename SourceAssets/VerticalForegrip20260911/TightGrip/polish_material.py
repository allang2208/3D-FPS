import bpy
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'VerticalForegrip_Refined.blend'))
o=bpy.data.objects['SM_VerticalForegrip'];m=bpy.data.materials['Body.001'];o.data.materials.clear();o.data.materials.append(m)
for f in o.data.polygons:f.material_index=0
bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
for uv in o.data.uv_layers.active.data:uv.uv=(.53+uv.uv.x*.12,.79+uv.uv.y*.05)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'VerticalForegrip_Refined.blend'))
bpy.ops.export_scene.fbx(filepath=str(O/'SM_VerticalForegrip.fbx'),use_selection=True,object_types={'MESH'},bake_anim=False,axis_forward='-Y',axis_up='Z',path_mode='COPY',embed_textures=True)
bpy.ops.export_scene.gltf(filepath=str(O/'VerticalForegrip_Refined.glb'),use_selection=True,export_apply=True)
