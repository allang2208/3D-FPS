"""Render the actual Aurora part for the gunsmith card, using the project's neutral studio setup."""
from pathlib import Path
import sys
import bpy
from mathutils import Vector
src=Path(__file__).resolve().parent
batch=Path(sys.argv[sys.argv.index('--')+1])
bpy.ops.wm.open_mainfile(filepath=str(src/'Frontier_Aurora.blend'))
scene=bpy.context.scene
scene.objects['Armature'].data.pose_position='REST'
include={'Riser'}
parts=[]
for obj in scene.objects:
    if obj.type=='MESH':
        obj.hide_render=not (obj.name.startswith('Aurora_') or obj.name in include)
        if not obj.hide_render:parts.append(obj)
    if obj.type=='LIGHT':obj.hide_render=True
world=bpy.data.worlds.new('Attachment studio');scene.world=world;world.use_nodes=True
world.node_tree.nodes.get('Background').inputs[0].default_value=(.41,.45,.49,1)
world.node_tree.nodes.get('Background').inputs[1].default_value=.7
cam_data=bpy.data.cameras.new('Card');cam_data.type='ORTHO';cam_data.clip_end=650
cam=bpy.data.objects.new('Card',cam_data);scene.collection.objects.link(cam);scene.camera=cam
direction=Vector((.10,1.,.055)).normalized()
cam.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
rot=cam.rotation_euler.to_matrix();coords=[rot.inverted()@(o.matrix_world@v.co) for o in parts for v in o.data.vertices]
lo=Vector(tuple(min(p[i] for p in coords) for i in range(3)));hi=Vector(tuple(max(p[i] for p in coords) for i in range(3)))
center=rot@((hi+lo)/2);cam.location=center+direction*164;cam_data.ortho_scale=max(hi.x-lo.x,hi.y-lo.y)/.82
for v,w,size,col in [((45,67,60),195000,62,(1.,.88,.76)),((-40,45,17),100000,50,(.81,.87,1.)),((22,-50,67),190000,56,(1.,.91,.80))]:
    light=bpy.data.lights.new('Studio softbox','AREA');light.energy=w;light.shape='DISK';light.size=size;light.color=col
    obj=bpy.data.objects.new('Studio softbox',light);scene.collection.objects.link(obj);obj.location=center+Vector(v);obj.rotation_euler=(-Vector(v)).to_track_quat('-Z','Y').to_euler()
scene.render.engine='CYCLES';scene.cycles.samples=20;scene.render.film_transparent=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.filepath=str(batch/'aurora_subject.png')
bpy.ops.render.render(write_still=True)
