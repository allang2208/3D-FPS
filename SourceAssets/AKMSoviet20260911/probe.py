import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O/'Source/ak47fbx_extracted/AK47NoSubdiv.fbx'))
report=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 pts=[o.matrix_world@v.co for v in o.data.vertices]
 report.append({'name':o.name,'vertices':len(pts),'bounds':[[min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]],'matrix':[list(x) for x in o.matrix_world],'materials':[m.name for m in o.data.materials]})
print(json.dumps(report));(O/'probe.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'SourceInspect.blend'))
s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='MATERIAL';s.display.shading.show_cavity=True;s.render.resolution_x=1400;s.render.resolution_y=700;s.render.resolution_percentage=100
pts=[o.matrix_world@v.co for o in s.objects if o.type=='MESH' for v in o.data.vertices];lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)]);target=(lo+hi)/2
d=bpy.data.cameras.new('Review');cam=bpy.data.objects.new('Review',d);s.collection.objects.link(cam);s.camera=cam;d.type='ORTHO';d.ortho_scale=max(hi-lo)*1.25
for tag,axis in [('x',(1,0,0)),('y',(0,1,0)),('z',(0,0,1))]:
 cam.location=target+Vector(axis)*max(hi-lo)*2;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'source_{tag}.png');bpy.ops.render.render(write_still=True)
