import bpy,math,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent
for gun in ['M4','AKM','QBZ']:
 file=S/('MagazineMouthFinish20260919/AKM_ExtMag_Mouth_Editable.blend' if gun=='AKM' else 'ExtMagPattern20260919/'+gun+'_ExtMag_Editable.blend')
 bpy.ops.wm.open_mainfile(filepath=str(file));ob=next(x for x in bpy.context.scene.objects if x.type=='MESH' and x.name.startswith('SM_ExtMag'));sc=bpy.context.scene
 for x in list(sc.objects):
  if x!=ob:bpy.data.objects.remove(x,do_unlink=True)
 pts=[v.co for v in ob.data.vertices];lo=Vector([min(v[i] for v in pts) for i in range(3)]);hi=Vector([max(v[i] for v in pts) for i in range(3)]);center=(lo+hi)/2
 cam=bpy.data.objects.new('DiagnosisCamera',bpy.data.cameras.new('DiagnosisCamera'));sc.collection.objects.link(cam);sc.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=max(hi-lo)*1.15
 sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='SINGLE';sc.display.shading.show_cavity=True;sc.render.resolution_x=600;sc.render.resolution_y=700;sc.render.resolution_percentage=100
 for view,off in [('side',(.6,0,0)),('edge',(.25,-.4,.09))]:
  cam.location=center+Vector(off);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(O/(gun+'_'+view+'_before.png'));bpy.ops.render.render(write_still=True)
