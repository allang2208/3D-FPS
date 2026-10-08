from pathlib import Path
import bpy,sys
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006');OUT=ROOT/'TentacleWhipV4'
version='v4' if '--v4' in sys.argv else 'v3'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/('TentacleWhipV4/BoundCongregate_TentacleV4.blend' if version=='v4' else 'TentacleWhipV3/BoundCongregate_TentacleV3.blend')))
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE')
for ob in list(scene.objects):
    if ob.type in ('CAMERA','LIGHT'):bpy.data.objects.remove(ob,do_unlink=True)
    elif ob.name.endswith('_SimulationProxy'):ob.hide_render=True
scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.threads_mode='FIXED';scene.render.threads=8
scene.world=bpy.data.worlds.new('RootDiagnosis');scene.world.color=(.25,.25,.25)
target=Vector((.77,.13,1.84))
for name,p,power,size in [('Key',(2,-3,5),850,3),('Fill',(-3,-1,3),600,3)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=p;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('Root');cam=bpy.data.objects.new('Root',d);scene.collection.objects.link(cam);scene.camera=cam
d.type='ORTHO';d.ortho_scale=1.6;cam.location=(2.3,-3.5,2.8);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
for name,action,frame in [('rest',None,1),('idle','A_BoundCongregate_IdleV3',31),('walk','A_BoundCongregate_WalkV2',13)]:
    rig.animation_data.action=bpy.data.actions[action] if action else None
    for pb in rig.pose.bones:pb.matrix_basis.identity()
    scene.frame_set(frame);bpy.context.view_layer.update()
    scene.render.filepath=str(OUT/f'root_source_{version}_{name}.png');bpy.ops.render.render(write_still=True)
