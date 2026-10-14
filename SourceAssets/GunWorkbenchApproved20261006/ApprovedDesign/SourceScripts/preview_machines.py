import bpy,pathlib,json
from mathutils import Vector
R=pathlib.Path(__file__).resolve().parents[1];bpy.ops.wm.read_factory_settings(use_empty=True);exec((R/'src/machine_props.py').read_text());materials();printer();press()
for name,off in [('Printer',(-.40,0,0)),('AmmoPress',(.40,0,0))]:
 c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c)
 for o in GROUPS[name]:
  o.location+=Vector(off)
  for old in list(o.users_collection):old.objects.unlink(o)
  c.objects.link(o)
# Separate presentation scene, not a tabletop layout.
group('Studio');floor=cube('Studio platform',(0,0,-.025),(200,200,.05),mat('Studio grey',(.035,.047,.057),0,.82),0)
def light(name,loc,power,size):
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,.3))-o.location).to_track_quat('-Z','Y').to_euler()
light('Key',(-2,-3,4),650,3);light('Fill',(3,-1,2.5),450,2.5);light('Rim',(0,3,3.5),850,2.5)
bpy.ops.object.camera_add(location=(1.5,-2.8,1.5));c=bpy.context.object;c.rotation_euler=(Vector((0,0,.35))-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=1.8;s=bpy.context.scene;s.camera=c;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True;s.world=bpy.data.worlds.new('Studio World');s.world.color=(.2,.2,.2);s.view_settings.view_transform='AgX';s.render.resolution_x=1600;s.render.resolution_y=1200;s.render.image_settings.file_format='PNG'
bpy.ops.wm.save_as_mainfile(filepath=str(R/'output/Machines_Design_Working.blend'));s.render.filepath=str(R/'output/Machines_Design_Preview.png');bpy.ops.render.render(write_still=True)
