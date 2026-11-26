"""Fast static authoring views from native skinned surfaces, before publishing."""
import bpy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
prefix=(P/'Tools/ChapelNun/review_crossed_author_contacts_r7.py').read_text(encoding='utf-8').split('visible=robe.t')[0]
exec(compile(prefix,'<native pose surfaces>','exec'))
bpy.ops.wm.read_factory_settings(use_empty=True)
w=fk(rig['frames'][0]);s=bpy.context.scene
for surface,name,rgb in [(body,'Hands',(.46,.29,.20,1)),(robe,'BlackHabit',(.14,.14,.15,1))]:
 p=surface.skin(w)
 if surface is body:
  mask=np.array([n.startswith(('hand_','thumb_','index_','middle_','ring_','pinky_')) for n in surface.dominant]);tris=surface.t[mask[surface.t].all(axis=1)]
 else:tris=surface.t[~np.isin(surface.m,[5,9])]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(p.tolist(),[],tris[:,::-1].tolist());mesh.update()
 obj=bpy.data.objects.new(name,mesh);s.collection.objects.link(obj)
 mat=bpy.data.materials.new(name);mat.diffuse_color=rgb;mesh.materials.append(mat)
 for poly in mesh.polygons:poly.use_smooth=True
from mathutils import Vector
import math
s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=960;s.render.resolution_y=960;s.render.resolution_percentage=100
s.display.shading.light='STUDIO';s.display.shading.studiolight_rotate_z=math.radians(35);s.display.shading.color_type='MATERIAL'
s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
s.display.shading.background_type='WORLD';s.world=bpy.data.worlds.new('ReviewWorld');s.world.color=(.12,.12,.12)
c=bpy.data.cameras.new('Review');ob=bpy.data.objects.new('Review',c);s.collection.objects.link(ob);s.camera=ob;c.type='ORTHO';c.clip_end=2000
O=R.parent/'AuthorViews';O.mkdir(exist_ok=True)
for name,eye,target,size in [('front',(0,300,110),(0,0,106),85),('side',(300,0,110),(0,0,106),85),('hands',(0,220,98),(0,20,91),42),('hands_side',(200,80,98),(0,20,93),55)]:
 ob.location=eye;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler();c.ortho_scale=size
 s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
