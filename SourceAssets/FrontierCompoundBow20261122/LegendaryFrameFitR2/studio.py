"""Offline fixed camera corresponding to the horizontal gunsmith side elevation; also render the part icons."""
from pathlib import Path
import os,sys,math
import bpy
from mathutils import Vector,Matrix
src=Path(__file__).resolve().parent
kind,rev,view=sys.argv[sys.argv.index('--')+1:]
path=src/('Frontier_'+kind+'.blend') if rev=='after' else src.parent/(kind+'FrameR1')/('Frontier_'+kind+'.blend')
bpy.ops.wm.open_mainfile(filepath=str(path))
scene=bpy.context.scene
rig=scene.objects['Armature'];rig.data.pose_position='REST';scene.frame_set(1)
active={'Riser','Grip','UpperLimb','LowerLimb','Rest','Stabilizer','UpperCam','LowerCam','ControlCable1','ControlCable2'}
if view=='icon':active={'Riser'}
for ob in scene.objects:
 if ob.type=='MESH':ob.hide_render=ob.name not in active and not ob.name.startswith(kind+'_')
 if ob.type=='LIGHT':ob.hide_render=True
world=bpy.data.worlds.new('Neutral workbench');world.use_nodes=True;scene.world=world
background=world.node_tree.nodes['Background'];background.inputs[0].default_value=(.21,.24,.28,1);background.inputs[1].default_value=.58
camdata=bpy.data.cameras.new('Workbench');camdata.type='ORTHO';camdata.clip_end=600
cam=bpy.data.objects.new('Workbench',camdata);scene.collection.objects.link(cam);scene.camera=cam
eye=Vector((.005,1.,.012)).normalized() if view!='oblique' else Vector((.22,.95,-.17)).normalized()
right=(Vector((0,0,1))-eye*eye.z).normalized();up=eye.cross(right)
if view=='icon':
 right=Vector((1,0,0)).cross(eye).cross(eye).normalized()
 up=eye.cross(right)
cam.rotation_euler=Matrix((right,up,eye)).transposed().to_euler()
center=Vector((3.2,0,5.0))
cam.location=center+eye*140
camdata.ortho_scale=76.8 if view!='icon' else 79.5
def light(offset,power,size,color):
 l=bpy.data.lights.new('Softbox','AREA');l.energy=power;l.shape='DISK';l.size=size;l.color=color
 ob=bpy.data.objects.new('Softbox',l);scene.collection.objects.link(ob);ob.location=center+Vector(offset)
 ob.rotation_euler=(-Vector(offset)).to_track_quat('-Z','Y').to_euler()
light((39,52,45),99000,52,(.95,.96,1.0));light((-30,30,-45),72000,62,(.78,.87,1.));light((19,-24,-50),82000,42,(1.,.88,.73))
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=1024 if view=='icon' else 1472
scene.render.resolution_y=1024 if view=='icon' else 510
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=(view=='icon')
scene.render.image_settings.color_mode='RGBA' if view=='icon' else 'RGB'
out=Path(os.environ['FIT_REVIEW']) if view!='icon' else Path(os.environ['FIT_BATCH'])
scene.render.filepath=str(out/(kind+'-'+rev+'-'+view+'.png'))
bpy.ops.render.render(write_still=True)
