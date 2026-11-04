import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
kind=sys.argv[sys.argv.index('--')+1]
bpy.ops.wm.open_mainfile(filepath=str(P/(kind+'_Editable.blend')))
data=json.loads((P/(kind+'.json')).read_text('utf-8'));obj=bpy.data.objects[data['object']]
for o in list(bpy.context.scene.objects):
 if o!=obj:bpy.data.objects.remove(o,do_unlink=True)
obj.hide_render=False;obj.hide_set(False)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True
s.render.resolution_x=s.render.resolution_y=900;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.film_transparent=True
s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast'
for layer in s.view_layers:layer.material_override=None
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
s.cycles.device='GPU'
s.world=bpy.data.worlds.new('ReviewWorld');s.world.use_nodes=True
bg=next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.3,.3,.3,1);bg.inputs[1].default_value=.6
points=[obj.matrix_world@Vector(v) for v in obj.bound_box];center=sum(points,Vector())/8
span=max(max(p.x for p in points)-min(p.x for p in points),max(p.z for p in points)-min(p.z for p in points))
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(cam);s.camera=cam
cam.data.type='ORTHO';cam.data.ortho_scale=span/.8;cam.data.clip_start=.001
lights=[]
for name,offset,power,size in [('Key',(.5,1,1),35,1.1),('Fill',(-.7,1,-.4),18,1.4),('Rim',(.3,-.5,1),35,.6)]:
 l=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));s.collection.objects.link(l);lights.append(l)
 l.location=center+Vector(offset)*span;l.rotation_euler=(center-l.location).to_track_quat('-Z','Y').to_euler();l.data.energy=power*span*span;l.data.size=size*span
clay=bpy.data.materials.new('DiagnosticFlatClay');clay.diffuse_color=(.3,.3,.3,1);clay.use_nodes=True
bs=next(n for n in clay.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.3,.3,.3,1);bs.inputs['Roughness'].default_value=.36
original=list(obj.data.materials)
for label,offset,is_clay in [('front',(0,4,0),False),('oblique',(1.6,4,1),False),('thickness',(4,1.1,.7),False),('clay',(1.6,4,1),True)]:
 obj.data.materials.clear()
 for m in ([clay] if is_clay else original):obj.data.materials.append(m)
 cam.location=center+Vector(offset)*span;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
 s.render.filepath=str(P/'Review'/(kind+'_'+label+'.png'));bpy.ops.render.render(write_still=True)
print('REVIEW_RENDERED '+kind,flush=True)
