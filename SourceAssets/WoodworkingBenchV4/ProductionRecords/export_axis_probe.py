import bpy
from pathlib import Path
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(size=1,location=(.870,.010,.903))
o=bpy.context.object;o.name='AxisProbe';o.dimensions=(.01,.02,.03)
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bpy.ops.export_scene.fbx(filepath='D:/FPS3D/FPSGAME/SourceAssets/WoodworkingBenchV4/GameReady/AxisProbe.fbx',use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',use_mesh_modifiers=True,bake_anim=False)
