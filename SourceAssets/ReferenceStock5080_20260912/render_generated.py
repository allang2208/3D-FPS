"""Inspect the actual 5080 textured master, without rebuilding its silhouette."""
import bpy,json,math,struct,hashlib
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
source=next(P.glob('reference_stock_high_textured_master*.glb'))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
report={'source':source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'postprocess':'preview transforms only; generated geometry and materials retained','meshes':[]}
points=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)])
center=(lo+hi)/2;span=max(hi-lo)
report['original_bounds']=list(hi-lo)
for o in meshes:
 o.data.calc_loop_triangles();report['meshes'].append({'name':o.name,'vertices':len(o.data.vertices),'triangles':len(o.data.loop_triangles),'materials':[m.name for m in o.data.materials if m],'uv_layers':len(o.data.uv_layers)})
 o.location=(o.location-center)/span;o.scale/=span
report['textures']=[{'name':i.name,'size':list(i.size)} for i in bpy.data.images if i.type=='IMAGE']
raw=next(P.glob('reference_stock_high_raw_geometry*.glb'))
with raw.open('rb') as f:
 magic,version,length=struct.unpack('<III',f.read(12));chunk,kind=struct.unpack('<II',f.read(8));doc=json.loads(f.read(chunk))
report['raw_geometry']={'source':raw.name,'bytes':raw.stat().st_size,'triangles':sum(doc['accessors'][p['indices']]['count']//3 for m in doc['meshes'] for p in m['primitives']),'sha256':hashlib.sha256(raw.read_bytes()).hexdigest()}
(P/'generated_mesh_report.json').write_text(json.dumps(report,indent=2))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True;s.render.resolution_x=1400;s.render.resolution_y=950;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('NeutralStudio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.2,.23,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.5
s.view_settings.view_transform='AgX';s.view_settings.exposure=.45
def aim(o):o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
for pos,power in [((-2,-3,4),330),((3,-2,2),230),((1,3,3),400)]:
 bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=power;o.data.size=3;aim(o)
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=1.35;s.camera=cam
for name,pos in [('front',(0,-3,.01)),('back',(0,3,.01)),('top',(.001,0,3)),('end',(3,0,.01)),('beauty',(2,-3,1.2))]:
 cam.location=pos;aim(cam);s.render.filepath=str(P/('generated_'+name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'ReferenceStock5080_Generated_Editable.blend'))
print('GENERATED_MESH_REVIEW',json.dumps(report),flush=True)
