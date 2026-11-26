"""Render the production PBR materials on the two native head references offline."""
import math,sys
import bpy,numpy as np
from mathutils import Vector
from pathlib import Path
S=Path(__file__).resolve().parents[2]/'SourceAssets/ModernTacticalSet20261113'
out=S/'HelmetContourR2/Review'
rig,rev=sys.argv[-2:]
bpy.ops.wm.open_mainfile(filepath=str(S/rev/'Models'/f'TS01_Helmet_{rig}_GAME.blend'))
sc=bpy.context.scene
head=bpy.data.objects['REFERENCE_ONLY_'+rig];head.hide_render=False;head.hide_set(False)
m=bpy.data.materials.new('Review head clay');m.use_nodes=True;bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
bs.inputs['Base Color'].default_value=(.28,.27,.25,1);bs.inputs['Roughness'].default_value=.81
head.data.materials.clear();head.data.materials.append(m)
for f in head.data.polygons:f.use_smooth=True
top=max(v.co.z for v in head.data.vertices);target=Vector((0,-.012,top-.099))
cam=bpy.data.cameras.new('Fit camera');cam.type='ORTHO';cam.ortho_scale=.348;cam.clip_start=.01
ob=bpy.data.objects.new('Fit camera',cam);sc.collection.objects.link(ob);sc.camera=ob
def light(name,offset,power,size):
    l=bpy.data.lights.new(name,'AREA');l.energy=power;l.shape='DISK';l.size=size
    o=bpy.data.objects.new(name,l);sc.collection.objects.link(o);o.location=target+Vector(offset)
    o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
light('Large softbox',(-.42,-.64,.55),23,.47);light('Fill',(.45,-.33,.19),11,.42);light('Rear strip',(.22,.42,.35),17,.28)
w=bpy.data.worlds.new('Fit studio');w.use_nodes=True;next(n for n in w.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.18,.20,.23,1);next(n for n in w.node_tree.nodes if n.type=='BACKGROUND').inputs[1].default_value=.72;sc.world=w
sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True
sc.render.resolution_x=396;sc.render.resolution_y=410;sc.render.resolution_percentage=100;sc.render.film_transparent=True;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA';sc.view_settings.view_transform='AgX';sc.view_settings.exposure=0
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='OPTIX';prefs.refresh_devices()
    if any(d.type=='OPTIX' for d in prefs.devices):
        for d in prefs.devices:d.use=d.type=='OPTIX'
        sc.cycles.device='GPU'
except RuntimeError:pass
for a,name in [(0,'front'),(.77,'quarter'),(math.pi*.5,'side')]:
    ob.location=target+Vector((math.sin(a)*.65,-math.cos(a)*.65,.012));ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=str(out/(rig+'_'+rev+'_'+name+'.png'));bpy.ops.render.render(write_still=True)
