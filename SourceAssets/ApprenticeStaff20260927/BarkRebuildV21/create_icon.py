"""Produce the inventory PNG from the authored mesh; no acceptance render."""
import bpy, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Staff_NaturalBark_V21.blend'))
for obj in bpy.context.scene.objects:obj.hide_render=obj.name!='SM_Staff_Base'
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True
world=bpy.data.worlds.new('StaffIconStudio');world.use_nodes=True
background=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND')
background.inputs[0].default_value=(.32,.38,.45,1)
background.inputs[1].default_value=.5;scene.world=world
camera=bpy.data.cameras.new('StaffIconCamera');obj=bpy.data.objects.new('StaffIconCamera',camera);scene.collection.objects.link(obj)
obj.location=(80,-250,18);obj.rotation_euler=(-obj.location).to_track_quat('-Z','Y').to_euler()
obj.rotation_euler.rotate_axis('Z',math.radians(-24));camera.type='ORTHO';camera.ortho_scale=175;scene.camera=obj
for name,location,energy,size,color in [
    ('Key',(-75,-90,135),1900000,110,(1,.84,.64)),
    ('Fill',(100,-20,55),1250000,80,(.73,.86,1)),
    ('Rim',(35,80,105),1800000,70,(1,.96,.87))]:
    light=bpy.data.lights.new(name,'AREA');light.energy=energy;light.shape='DISK';light.size=size;light.color=color
    ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=location
    ob.rotation_euler=(Vector((0,0,25))-ob.location).to_track_quat('-Z','Y').to_euler()
scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.filepath=str(ROOT/'Export/apprentice_staff.png')
bpy.ops.render.render(write_still=True)
print('STAFF_V21_INVENTORY_ICON_SAVED')
