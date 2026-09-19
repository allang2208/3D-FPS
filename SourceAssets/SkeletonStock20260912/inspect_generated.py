import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(P/'skeleton_raw.glb'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
report={o.name:{'vertices':len(o.data.vertices),'polygons':len(o.data.polygons),'dimensions':list(o.dimensions)} for o in meshes}
(P/'raw_inspection.json').write_text(json.dumps(report,indent=2))
pts=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box];lo=Vector([min(v[i] for v in pts) for i in range(3)]);hi=Vector([max(v[i] for v in pts) for i in range(3)]);center=(lo+hi)/2;span=max(hi-lo)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True;s.render.resolution_x=900;s.render.resolution_y=700;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('Studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.25,.25,.25,1)
def aim(o):o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=span*1.4;s.camera=cam
for loc,power in [((1,-2,3),500),((-2,-1,1),350),((0,2,2),600)]:
 bpy.ops.object.light_add(type='AREA',location=center+Vector(loc)*span);o=bpy.context.object;o.data.energy=power*span*span;o.data.size=span*2;aim(o)
for name,loc in [('front',(0,-3,0)),('side',(3,0,0)),('beauty',(2,-3,1))]:
 cam.location=center+Vector(loc)*span;aim(cam);s.render.filepath=str(P/('raw_'+name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'SkeletonStock_Raw.blend'));print('STOCK_RAW_INSPECT_PASS',json.dumps(report))
