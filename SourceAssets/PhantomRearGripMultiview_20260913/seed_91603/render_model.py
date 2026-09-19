import bpy, math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(next(P.glob('textured_master*.glb'))))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
points=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
lo=Vector([min(p[i] for p in points) for i in range(3)])
hi=Vector([max(p[i] for p in points) for i in range(3)])
center=(lo+hi)/2;span=max(hi-lo)
for o in meshes:
    o.location=(o.location-center)/span;o.scale/=span
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True
s.render.resolution_x=1000;s.render.resolution_y=1100;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('Studio');s.world.use_nodes=True
s.world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.21,.25,1)
s.world.node_tree.nodes['Background'].inputs[1].default_value=.5
s.view_settings.view_transform='AgX';s.view_settings.exposure=.5
def aim(o):o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
for pos,power in [((-2,-3,4),330),((3,-2,2),250),((1,3,3),400)]:
    bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=power;o.data.size=3;aim(o)
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=1.35;s.camera=cam
for name,pos in [('front',(0,-3,.05)),('back',(0,3,.05)),('angle',(3,1.5,.7)),('side',(3,0,.05))]:
    cam.location=pos;aim(cam);s.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'PhantomRearGrip_Multiview_Editable.blend'))
