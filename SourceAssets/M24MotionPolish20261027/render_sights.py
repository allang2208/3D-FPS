"""Scoped source-surface review of the two user-reported sight assemblies."""
import bpy,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_PalmaIron_Editable.blend'),use_scripts=False)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
s.render.resolution_x=960;s.render.resolution_y=720;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.render.use_compositing=False;s.render.use_sequencer=False
s.world=bpy.data.worlds.new('Sight review');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.21,.26,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.3
bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.095;cam.data.clip_start=.001
lights=[]
for p,energy,size in [((.08,-.05,.24),10,.15),((-.08,.10,.21),12,.10),((.0,.0,.25),4,.1)]:
 bpy.ops.object.light_add(type='AREA',location=p);l=bpy.context.object;l.data.energy=energy;l.data.shape='DISK';l.data.size=size;lights.append(l)
for family,target in [('rear',Vector((-.009,.055,.144))),('front',Vector((0,.795,.145)))]:
 for ob in s.objects:
  if ob.type=='MESH':ob.hide_render=not ob.name.startswith(family.capitalize()+'_')
 cam.location=target+Vector((.08,-.08,.045));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
 for l,offset in zip(lights,[(.08,-.1,.10),(-.08,.06,.08),(.0,.0,.13)]):l.location=target+Vector(offset);l.rotation_euler=(target-l.location).to_track_quat('-Z','Y').to_euler()
 s.render.filepath=str(O/('sight_'+family+'.png'));bpy.ops.render.render(write_still=True)
