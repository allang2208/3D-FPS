"""Production attachment icons from the actual rebuilt meshes, not acceptance renders."""
import bpy,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;(O/'Icons').mkdir(exist_ok=True)
for gun,weapon,color,metal in [('AKM','ue_akm',(.055,.061,.068,1),.8)]:
 bpy.ops.wm.open_mainfile(filepath=str(O/('AKM_ExtMag_Closed_Editable.blend')));s=bpy.context.scene
 ob=bpy.data.objects['SM_ExtMag_AKM40_Closed'];ob.hide_set(False);ob.hide_render=False
 for other in list(s.objects):
  if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
 points=[ob.matrix_world@v.co for v in ob.data.vertices];lo=Vector([min(p[k] for p in points) for k in range(3)]);hi=Vector([max(p[k] for p in points) for k in range(3)]);c=(lo+hi)/2;size=max(hi-lo)
 cam=bpy.data.objects.new('IconCamera',bpy.data.cameras.new('IconCamera'));s.collection.objects.link(cam);cam.location=c+Vector((size*3,0,0));cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=size*1.20;s.camera=cam
 for name,offset,power,width in [('Key',(1,-1,2),45,.5),('Fill',(1,1,.3),20,.4),('Rim',(-1,0,1),30,.4)]:
  d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=width;l=bpy.data.objects.new(name,d);s.collection.objects.link(l);l.location=c+Vector(offset)*.45;l.rotation_euler=(c-l.location).to_track_quat('-Z','Y').to_euler()
 s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True;s.render.film_transparent=True;s.render.resolution_x=1024;s.render.resolution_y=1024;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.filepath=str(O/'Icons'/(weapon+'_magazine_ext_mag.png'));bpy.ops.wm.save_as_mainfile(filepath=str(O/(gun+'_IconStudio.blend')));bpy.ops.render.render(write_still=True)
