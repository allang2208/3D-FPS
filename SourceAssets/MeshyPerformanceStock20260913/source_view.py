import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent;R=P.parent
import math
from mathutils import Matrix
stage='meshy'
bpy.ops.wm.open_mainfile(filepath=str(P/'Imported.blend'));ob=next(o for o in bpy.context.scene.objects if o.type=='MESH')
ob.matrix_world=Matrix.Rotation(math.pi/2,4,'Z')@ob.matrix_world
pts=[ob.matrix_world@v.co for v in ob.data.vertices];lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)]);c=(lo+hi)/2;span=max(hi-lo)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=64;s.cycles.use_denoising=False;s.render.resolution_x=1000;s.render.resolution_y=1000;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('Diagnosis');s.world.use_nodes=True;next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.19,.19,.19,1);s.view_settings.view_transform='AgX'
for off,power,size in [((2,-2,3),350,2),((-2,-1,1),220,2),((1,3,2),450,1.5)]:
 bpy.ops.object.light_add(type='AREA',location=c+Vector(off)*span);o=bpy.context.object;o.data.energy=power*span*span;o.data.shape='DISK';o.data.size=size*span;o.rotation_euler=(c-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=c+Vector((3,-1.7,1))*span);cam=bpy.context.object;cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=span*1.2;s.camera=cam
original=[bpy.data.materials.new('Diagnostic')];original[0].use_nodes=True
report={'stage':stage,'vertices':len(ob.data.vertices),'triangles':sum(len(f.vertices)-2 for f in ob.data.polygons)}
for f in ob.data.polygons:f.material_index=0
for mode in ['clay']:
 ob.data.materials.clear()
 for src in original:
  m=src.copy();ob.data.materials.append(m);bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
  def setpin(pin,value):
   for link in list(bs.inputs[pin].links):m.node_tree.links.remove(link)
   if value is not None:bs.inputs[pin].default_value=value
  setpin('Normal',None);setpin('Metallic',.8);setpin('Roughness',.38)
  if mode in ['flat_color','rough_coating','clay']:setpin('Base Color',(.025,.029,.032,1) if 'Polymer' not in src.name else (.014,.016,.018,1))
  if mode=='rough_coating':setpin('Roughness',.62);setpin('Metallic',.0)
  if 'clay' in mode:setpin('Base Color',(.3,.32,.34,1));setpin('Metallic',0.);setpin('Roughness',.6)
 if mode=='back_clay':
  cam.location=c+Vector((-3,0,0))*span;cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler()
 s.render.filepath=str(P/(stage+'_'+mode+'.png'));bpy.ops.render.render(write_still=True)
 if mode=='flat_color':bpy.ops.wm.save_as_mainfile(filepath=str(P/'Meshy_Review.blend'))
(P/(stage+'_report.json')).write_text(json.dumps(report,indent=2))
