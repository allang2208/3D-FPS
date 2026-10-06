"""Produce the shared attachment icon source, not a gameplay/acceptance render."""
import bpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parents[3];O=P/'SourceAssets/LegendaryStock20261006/RefinementV3'
O.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'SourceAssets/LegendaryStock20261006/Model/TacticalStock_Editable.blend'))
for mat in bpy.data.materials:
 if not mat.use_nodes:continue
 bs=mat.node_tree.nodes.get('Principled BSDF')
 if bs:
  c=bs.inputs['Base Color'].default_value;g=.2126*c[0]+.7152*c[1]+.0722*c[2]
  if bs.inputs['Base Color'].is_linked:
   old=bs.inputs['Base Color'].links[0].from_socket
   gray=mat.node_tree.nodes.new('ShaderNodeRGBToBW')
   mat.node_tree.links.new(old,gray.inputs['Color'])
   mat.node_tree.links.new(gray.outputs['Val'],bs.inputs['Base Color'])
  else:bs.inputs['Base Color'].default_value=(g,g,g,1)
  bs.inputs['Emission Strength'].default_value=0
target=Vector((-.143,0,-.037))
def look(ob):ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(-.120,.85,.105));cam=bpy.context.object;look(cam)
cam.data.type='ORTHO';cam.data.ortho_scale=.365;bpy.context.scene.camera=cam
for position,power,size in [((.1,.3,.5),5,.45),((-.4,.25,.15),2.5,.35),((-.15,-.2,.4),4,.35)]:
 bpy.ops.object.light_add(type='AREA',location=position);lamp=bpy.context.object
 lamp.data.energy=power;lamp.data.shape='DISK';lamp.data.size=size;look(lamp)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48
s.render.resolution_x=1024;s.render.resolution_y=1024;s.render.resolution_percentage=100;s.render.film_transparent=True
s.world=bpy.data.worlds.new('Attachment icon studio');s.world.color=(.2,.2,.2);s.view_settings.view_transform='AgX'
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
s.render.filepath=str(O/'tactical-stock-icon-source.png');bpy.ops.render.render(write_still=True)
print('TACTICAL_STOCK_ICON_SOURCE '+s.render.filepath,flush=True)
