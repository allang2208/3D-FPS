"""The real flexible string laid in loose coils for its catalog photograph."""
from pathlib import Path
import bpy,math
from mathutils import Vector
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P/'MountainEcho_String.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
obj=bpy.data.objects['SK_Highland_MountainEchoString']
obj.modifiers.clear();obj.parent=None
for o in list(scene.objects):
    if o.type=='ARMATURE':bpy.data.objects.remove(o,do_unlink=True)
low=-77.95815;high=88.33999;x=-17.36598
for v in obj.data.vertices:
    t=(v.co.z-low)/(high-low);a=t*math.tau*6.25+.5;radius=3.9+.55*t
    offset=v.co.x-x
    v.co=((radius+offset)*math.cos(a),v.co.y+.12*math.sin(t*math.tau)+.025*t,(radius+offset)*math.sin(a))
for m in obj.data.materials:
    bs=m.node_tree.nodes.get('Principled BSDF');c=bs.inputs['Base Color'].default_value
    grey=c[0]*.2126+c[1]*.7152+c[2]*.0722
    bs.inputs['Base Color'].default_value=(grey,grey,grey,1)
scene.render.engine='CYCLES';scene.cycles.samples=64
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True
scene.world=bpy.data.worlds.new('Neutral studio');scene.world.use_nodes=True
scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.18,.18,.18,1)
scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.4
for name,pos,energy,size in [('Key',(-5,-8,10),1000,8),('Fill',(6,-5,4),600,6),('Rim',(1,4,8),1100,5)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=pos
    o.rotation_euler=(Vector((0,0,0))-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('Catalog camera');cam=bpy.data.objects.new('Catalog camera',d);scene.collection.objects.link(cam)
cam.location=(0,-22,2);cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=10.4;scene.camera=cam
scene.view_settings.view_transform='AgX'
bpy.ops.wm.save_as_mainfile(filepath=str(P/'MountainEcho_Icon_Input.blend'))
scene.render.filepath=str(P/'MountainEcho_Icon_Input.png');bpy.ops.render.render(write_still=True)
