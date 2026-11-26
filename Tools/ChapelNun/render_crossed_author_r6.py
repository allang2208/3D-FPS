"""Front and side authoring views for the requested crossed-hand correction."""
import bpy,math
from pathlib import Path
from mathutils import Vector
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/IdleCrossedR6')
O=R/'AuthorViews';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'Nun_Crossed_Idle_R6.blend'))
s=bpy.context.scene;s.frame_set(1);s.render.engine='BLENDER_WORKBENCH'
s.render.resolution_x=960;s.render.resolution_y=960;s.render.resolution_percentage=100
s.display.shading.light='STUDIO';s.display.shading.studiolight_rotate_z=math.radians(35)
s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
s.display.shading.background_type='WORLD';s.world=s.world or bpy.data.worlds.new('ReviewWorld');s.world.color=(.12,.12,.12)
for m in bpy.data.materials:
 if 'BlackHabit' in m.name:m.diffuse_color=(.15,.15,.16,1)
c=bpy.data.cameras.new('Review');ob=bpy.data.objects.new('Review',c);s.collection.objects.link(ob);s.camera=ob;c.type='ORTHO';c.clip_end=2000
for name,eye,target,size in [('front',(0,300,110),(0,0,106),85),('side',(300,0,110),(0,0,106),85),('hands',(0,220,98),(0,20,87),42),('hands_side',(200,80,98),(0,20,89),55)]:
 ob.location=eye;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler();c.ortho_scale=size
 s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
