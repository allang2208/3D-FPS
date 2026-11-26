"""Scoped inspection renders requested by the user; authored native surface."""
import bpy, math
from pathlib import Path
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChapelNun20261115/IdleBackReviewR2'
O=R/'SourceAfter';O.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'SourceAssets/ChapelNun20261115/IdleHandsFrontR2/Nun_HandsFront_Idle_R2.blend'))
s=bpy.context.scene;s.frame_set(1);s.render.engine='BLENDER_WORKBENCH'
s.render.resolution_x=960;s.render.resolution_y=960;s.render.resolution_percentage=100
s.display.shading.light='STUDIO';s.display.shading.studiolight_rotate_z=math.radians(35)
s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=True
s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
s.display.shading.background_type='WORLD';s.world=s.world or bpy.data.worlds.new('ReviewWorld');s.world.color=(.12,.12,.12)
cam=bpy.data.cameras.new('ReviewCamera');ob=bpy.data.objects.new('ReviewCamera',cam);s.collection.objects.link(ob);s.camera=ob;cam.type='ORTHO';cam.clip_end=2000
for name,eye,target,size in [('front',(0,300,135),(0,0,105),105),('back',(0,-220,147),(0,0,133),58),('hands',(0,220,111),(0,23,97),48),('hands_side',(170,160,112),(0,23,98),55)]:
 ob.location=eye;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler();cam.ortho_scale=size
 s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
print('NUN_SOURCE_REVIEW_RENDERED',flush=True)
