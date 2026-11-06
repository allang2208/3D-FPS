from pathlib import Path
import bpy
from mathutils import Vector

P=Path(__file__).resolve().parent
O=P/'Review20261106';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'Highland_GaleOath_GameModel.blend'))
s=bpy.context.scene
for obj in s.objects:
    obj.hide_render=obj.name!='SM_Highland_Pommel_GaleOath_R2'
    obj.hide_set(obj.hide_render)
model=bpy.data.objects['SM_Highland_Pommel_GaleOath_R2']
grip=bpy.data.objects['REFERENCE_Highland_Grip_native']
s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
s.cycles.device='GPU'
s.render.resolution_x=1200;s.render.resolution_y=1300;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
s.render.film_transparent=False
s.world=bpy.data.worlds.new('Review neutral studio');s.world.use_nodes=True
s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.16,.19,.23,1)
s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45
s.view_settings.view_transform='AgX'
def light(name,position,power,size,color):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    o=bpy.data.objects.new(name,data);s.collection.objects.link(o);o.location=position
    o.rotation_euler=(Vector((0,0,-.055))-o.location).to_track_quat('-Z','Y').to_euler()
light('Large cool key',(-.15,-.22,.15),8,.20,(.92,.96,1.))
light('Broad soft fill',(.19,-.15,-.045),5,.18,(1.,.97,.90))
light('Rim',(.10,.12,.05),10,.13,(.92,.97,1.))
c=bpy.data.objects.new('Review camera',bpy.data.cameras.new('Review camera'));s.collection.objects.link(c);s.camera=c
c.data.type='ORTHO';c.data.clip_start=.001;c.data.clip_end=10
for name,offset,target,scale,show_grip in [
    ('01_front',(0,-.4,0),(0,0,-.059),.145,False),
    ('02_three_quarter',(.23,-.4,.055),(0,0,-.059),.15,False),
    ('03_grip_joint',(.15,-.4,.08),(0,0,-.005),.095,True),
    ('04_back',(.12,.4,.035),(0,0,-.059),.15,False)]:
    grip.hide_render=not show_grip;grip.hide_set(not show_grip)
    c.location=Vector(target)+Vector(offset);c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler()
    c.data.ortho_scale=scale;s.render.filepath=str(O/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    print('GALE_OATH_REVIEW_RENDERED '+name,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'GaleOath_Review.blend'))
