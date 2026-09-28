import bpy, math
from pathlib import Path
from mathutils import Vector
R=Path('D:/FPS3D/FPSGAME/SourceAssets/GodSpaceLayout20260927');bpy.ops.wm.open_mainfile(filepath=str(R/'GodSpace_Layout_V1.blend'));s=bpy.context.scene
c=bpy.data.objects['Preview overlook'];c.location=(38.4,8,2.4);c.rotation_euler=(Vector((680,130,-360))-c.location).to_track_quat('-Z','Y').to_euler();c.data.lens=24
# Keep only low foreground cloud masses; they should not overwhelm the distant land.
for o in bpy.data.objects:
 if o.name.startswith('NEW cloud depth silhouette'):
  o.scale*=.65
  o.location.z-=80
ma=bpy.data.materials['Cloud hero volumes - offline preview']
for n in ma.node_tree.nodes:
 if n.type=='MATH' and n.operation=='MULTIPLY' and not n.inputs[1].is_linked:n.inputs[1].default_value=.012
s.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.5
s.cycles.samples=56;s.cycles.volume_bounces=2
s.camera=bpy.data.objects['Preview aerial']
bpy.ops.wm.save_as_mainfile(filepath=str(R/'GodSpace_Layout_V1.blend'))
for name,cam in [('godspace_aerial',bpy.data.objects['Preview aerial']),('godspace_overlook',c),('godspace_arrival',bpy.data.objects['Preview arrival'])]:
 s.camera=cam;s.render.filepath=str(R/'Preview'/(name+'.png'));bpy.ops.render.render(write_still=True)
