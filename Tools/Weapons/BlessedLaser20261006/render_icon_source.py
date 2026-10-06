"""Produce the one shared gunsmith icon source from the actual game master."""
import bpy,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parents[3]
O=P/'SourceAssets/BlessedLaser20261006/Model'
bpy.ops.wm.open_mainfile(filepath=str(O/'BlessedLaser_GameMaster.blend'))
for m in bpy.data.materials:
    if not m.use_nodes:continue
    bs=m.node_tree.nodes.get('Principled BSDF')
    if bs:
        c=bs.inputs['Base Color'].default_value
        grey=.2126*c[0]+.7152*c[1]+.0722*c[2]
        bs.inputs['Base Color'].default_value=(grey,grey,grey,1)
        bs.inputs['Emission Strength'].default_value=0
target=Vector((-.036,0,.001))
def look(ob):ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(.075,.18,.064))
camera=bpy.context.object;look(camera);camera.data.type='ORTHO';camera.data.ortho_scale=.096
bpy.context.scene.camera=camera
for position,power,size in [((.09,.06,.13),18,.13),((-.10,.04,.055),12,.09),((-.02,-.10,.11),20,.10)]:
    bpy.ops.object.light_add(type='AREA',location=position);lamp=bpy.context.object;lamp.data.energy=power;lamp.data.shape='DISK';lamp.data.size=size;look(lamp)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48
s.render.resolution_x=768;s.render.resolution_y=768;s.render.resolution_percentage=100
s.render.film_transparent=True
s.world=bpy.data.worlds.new('Icon studio')
s.world.color=(.15,.15,.15)
s.view_settings.view_transform='AgX'
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
s.render.filepath=str(O/'blessed-emitter-icon-source.png')
bpy.ops.render.render(write_still=True)
print('BLESSED_ICON_SOURCE_SAVED '+s.render.filepath,flush=True)
