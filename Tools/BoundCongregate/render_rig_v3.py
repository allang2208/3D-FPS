"""User-requested deformation review using the real mesh, UVs and skin weights."""
from pathlib import Path
import bpy, sys
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/RigRepairV3');OUT=ROOT/'Preview';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'BoundCongregate_RigV3.blend'))
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE')
rig.animation_data.action=bpy.data.actions['A_BoundCongregate_WalkV2']
for ob in list(scene.objects):
    if ob.type in ('CAMERA','LIGHT'):bpy.data.objects.remove(ob,do_unlink=True)
scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
scene.render.resolution_x=960;scene.render.resolution_y=760;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.threads_mode='FIXED';scene.render.threads=8
scene.view_settings.view_transform='AgX';scene.world=bpy.data.worlds.new('RigReview');scene.world.use_nodes=True
nodes=scene.world.node_tree.nodes;nodes.clear();bg=nodes.new('ShaderNodeBackground');output=nodes.new('ShaderNodeOutputWorld')
scene.world.node_tree.links.new(bg.outputs[0],output.inputs['Surface']);bg.inputs[0].default_value=(.19,.21,.23,1);bg.inputs[1].default_value=.4
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.025));floor=bpy.context.object
mat=bpy.data.materials.new('ReviewFloor');mat.diffuse_color=(.12,.13,.15,1);floor.data.materials.append(mat)
target=Vector((0,0,1.05))
for name,location,power,size in [('Key',(-3,-4,6),1100,4),('Fill',(4,-2,3),700,3),('Rim',(1,4,5),900,3)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=location;ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',data);scene.collection.objects.link(cam);scene.camera=cam
data.type='ORTHO';data.ortho_scale=5.3
views=[('right',(7,-1,3.1)),('front',(4.9,-7.7,3.6)),('left',(-6,-3,3.3))]
if '--rig-review-motion' in sys.argv:views=[views[0]]
for name,location in views:
    cam.location=location;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    for frame in (range(1,49,2) if '--rig-review-motion' in sys.argv else [7,25]):
        scene.frame_set(frame);scene.render.filepath=str(OUT/(name+'_'+str(frame).zfill(3)+'.png'));bpy.ops.render.render(write_still=True)
print('RIG_REVIEW_RENDERED',flush=True)
