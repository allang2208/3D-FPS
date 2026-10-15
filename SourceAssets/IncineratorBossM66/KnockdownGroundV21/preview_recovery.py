"""Requested diagnosis: source poses and floor contacts, not in-game acceptance."""
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/M66_recovery_v21.blend'))
rig=bpy.data.objects['M66_Rig'];mesh=bpy.data.objects['M66_Body'];floor_z=min(v.co.z for v in mesh.data.vertices)
code=(ROOT/'preview_support_pose.py').read_text('utf-8').split('scene=bpy.context.scene\n',1)[1]
code='scene=bpy.context.scene\n'+code
code=code.split("scene.render.filepath=str(ROOT/'Records/down-support-prototype.png')")[0]
exec(compile(code,'M66_recovery_diagnostic_scene','exec'))
for material,color in ((mesh.data.materials[0],(.32,.36,.38,1)),(ground.data.materials[0],(.20,.21,.23,1))):
 material.use_nodes=True;material.node_tree.nodes.clear()
 bs=material.node_tree.nodes.new('ShaderNodeBsdfPrincipled');bs.inputs[0].default_value=color
 out=material.node_tree.nodes.new('ShaderNodeOutputMaterial');material.node_tree.links.new(bs.outputs[0],out.inputs[0])
scene.render.image_settings.file_format='PNG'
for t in (0.,.6,1.4,2.6):
 scene.frame_set(round(t*60));scene.render.filepath=str(ROOT/'Records'/('recovery-'+str(round(t*10)).zfill(2)+'.png'))
 bpy.ops.render.render(write_still=True)
