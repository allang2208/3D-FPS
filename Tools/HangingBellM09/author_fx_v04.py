"""Author M09 reusable pulse geometry and original synthesized creature cues."""
import bpy,math,json
from pathlib import Path
ROOT=Path("D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/MotionV04")
(ROOT/"FX").mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_torus_add(major_radius=1.,minor_radius=.009,major_segments=64,minor_segments=6)
obj=bpy.context.object;obj.name="SM_M09_Wave"
bpy.ops.export_scene.fbx(filepath=str(ROOT/"FX/SM_M09_Wave.fbx"),use_selection=True,object_types={"MESH"},axis_forward="-Z",axis_up="Y",apply_unit_scale=True,bake_anim=False)
