import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).parent
asset=sys.argv[sys.argv.index('--')+1]
source=P/(asset+'.glb') if (P/(asset+'.glb')).exists() else next(P.glob(asset+'_baseline_textured_master*.glb'))
prefix=asset
upright='upright' in sys.argv
if upright: prefix+='_upright'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
if upright:
    for o in objects:o.matrix_world=Matrix.Rotation(math.pi/2,4,'Y')@o.matrix_world
points=[o.matrix_world@Vector(v) for o in objects for v in o.bound_box]
lo=Vector(tuple(min(p[i] for p in points) for i in range(3)))
hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
center=(lo+hi)/2; size=max(hi-lo)
for o in objects:
    o.location=(o.location-center)/size;o.scale/=size
    # Preview approximation: allow studio lighting through refractive glass,
    # avoiding the opaque shadow of non-caustic path tracing. Geometry unchanged.
    if 'Glass vessel' in o.name: o.visible_shadow=False
bpy.context.view_layer.update()
report={'asset':asset,'source':source.name,'bounds_original':list(hi-lo),'meshes':[]}
for o in objects:
    o.data.calc_loop_triangles()
    report['meshes'].append({'name':o.name,'vertices':len(o.data.vertices),'triangles':len(o.data.loop_triangles),'materials':[m.name for m in o.data.materials if m],'uv_layers':len(o.data.uv_layers)})
report['textures']=[{'name':i.name,'size':list(i.size)} for i in bpy.data.images if i.type=='IMAGE']
(P/(prefix+'_mesh_report.json')).write_text(json.dumps(report,indent=2))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True;s.cycles.transmission_bounces=12
s.render.resolution_x=900;s.render.resolution_y=900;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('Studio');s.world.use_nodes=True
s.world.node_tree.nodes['Background'].inputs[0].default_value=(.15,.15,.15,1)
s.world.node_tree.nodes['Background'].inputs[1].default_value=.5
def aim(o):o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=1.4;s.camera=cam
for pos,energy in [((-3,-4,5),400),((4,-2,3),250),((1,3,4),450)]:
    bpy.ops.object.light_add(type='AREA',location=pos);a=bpy.context.object;a.data.energy=energy;a.data.shape='DISK';a.data.size=3;aim(a)
s.view_settings.view_transform='AgX'
for name,pos in [('front',(0,-3,.1)),('back',(0,3,.1)),('beauty',(2,-3,1.6))]:
    cam.location=pos;aim(cam);s.render.filepath=str(P/(prefix+'_'+name+'.png'));bpy.ops.render.render(write_still=True)
cam.location=(2,-3,1.6);aim(cam)
bpy.ops.wm.save_as_mainfile(filepath=str(P/(prefix+'_candidate.blend')))
print(json.dumps(report),flush=True)
