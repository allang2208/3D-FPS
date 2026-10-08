"""Read the supplied GLB and record the requested model suitability evidence."""
import bpy, json, math, hashlib, shutil
from pathlib import Path
from mathutils import Vector
import numpy as np

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
SOURCE = Path('C:/Users/allan/Downloads/Meshy_AI_Fleshmaw_Leviathan_1006141038_texture.glb')
for folder in ['Original', 'Assessment', 'Textures', 'Authoring', 'Exports', 'Records']:
    (ROOT/folder).mkdir(parents=True, exist_ok=True)
dest = ROOT/'Original'/SOURCE.name
if not dest.exists(): shutil.copy2(SOURCE, dest)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(dest))
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
report = {'source':str(SOURCE), 'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
          'meshes':[], 'armatures':[], 'images':[]}
allpts=[]
for o in meshes:
    pts=np.array([tuple(o.matrix_world@v.co) for v in o.data.vertices])
    allpts.extend(pts.tolist())
    o.data.calc_loop_triangles()
    report['meshes'].append({'name':o.name,'vertices':len(o.data.vertices),
      'triangles':len(o.data.loop_triangles),'uv_layers':[u.name for u in o.data.uv_layers],
      'materials':[m.name if m else None for m in o.data.materials],
      'bounds':[pts.min(0).tolist(),pts.max(0).tolist()],
      'vertex_groups':len(o.vertex_groups)})
    # Numeric surface and connectivity are retained for anatomical authoring.
    np.savez_compressed(ROOT/'Assessment'/(o.name.replace('/','_')+'.npz'),
       vertices=pts, triangles=np.array([t.vertices[:] for t in o.data.loop_triangles]))
for o in bpy.context.scene.objects:
    if o.type=='ARMATURE':report['armatures'].append({'name':o.name,'bones':len(o.data.bones)})
for im in bpy.data.images:
    if im.type not in {'IMAGE','UV_TEST'} or not im.has_data:continue
    report['images'].append({'name':im.name,'size':list(im.size),'color_space':im.colorspace_settings.name})
    im.filepath_raw=str(ROOT/'Textures'/(im.name.rsplit('.',1)[0]+'.png'));im.file_format='PNG';im.save()
pts=np.asarray(allpts);lo=pts.min(0);hi=pts.max(0);center=Vector((lo+hi)/2);size=float(max(hi-lo))
report['bounds']=[lo.tolist(),hi.tolist()]
(ROOT/'Assessment/source_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/Source_Imported.blend'))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=1100;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('AssessmentWorld');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.28,.28,.28,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
scene.view_settings.view_transform='AgX'
for name,offset,power,area in [('Key',(1,-2,3),1100,3),('Fill',(-2,-1,1.5),650,2),('Rim',(0,2,2),900,2)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power*size*size;data.shape='DISK';data.size=area*size
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=center+Vector(offset)*size
    ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('AssessmentCamera');cam=bpy.data.objects.new('AssessmentCamera',camdata)
scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.ortho_scale=size*1.12
for name,direction in [('front',(0,-1,.14)),('back',(0,1,.14)),('left',(-1,0,.12)),('right',(1,0,.12)),('top',(0,-.05,1))]:
    cam.location=center+Vector(direction)*size*3;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(ROOT/'Assessment'/f'{name}.png');bpy.ops.render.render(write_still=True)
print(json.dumps(report,ensure_ascii=False))
