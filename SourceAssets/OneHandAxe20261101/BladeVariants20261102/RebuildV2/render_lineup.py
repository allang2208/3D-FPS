"""One actual-model comparison render for the requested individual redesign review."""
import bpy,json,runpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene
for kind,x in [('SwiftCrescent',.235),('HeavyCleaver',0),('FoldedArc',-.235)]:
    entry=json.loads((P/(kind+'.json')).read_text('utf-8'))
    with bpy.data.libraries.load(str(P/(kind+'_Editable.blend')),link=False) as (available,loaded):loaded.objects=[entry['object']]
    obj=loaded.objects[0];s.collection.objects.link(obj);obj.hide_render=False;obj.hide_set(False)
    center=sum((Vector(v) for v in obj.bound_box),Vector())/8
    obj.location=Vector((x,0,0))-center
s.render.engine='CYCLES';s.cycles.samples=64;s.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
s.cycles.device='GPU'
s.render.resolution_x=1650;s.render.resolution_y=650;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.film_transparent=True
s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast'
s.world=bpy.data.worlds.new('ReviewWorld');s.world.use_nodes=True
bg=next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.3,.3,.3,1);bg.inputs[1].default_value=.6
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(cam);s.camera=cam
cam.location=(0,3,.4);cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO';cam.data.ortho_scale=.74;cam.data.clip_start=.001
for name,loc,power,size in [('Key',(.1,.6,.7),40,1),('Fill',(-.5,.6,-.3),15,1),('Rim',(.2,-.4,.7),30,.6)]:
    light=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));s.collection.objects.link(light)
    light.location=loc;light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler();light.data.energy=power;light.data.size=size
s.render.filepath=str(P/'Review/ThreeBlades_R2.png')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'ThreeBlades_Review.blend'))
bpy.ops.render.render(write_still=True)
