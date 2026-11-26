"""Static geometry views for the requested female upper-back inspection."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/KaitlinBackReview20261117'
O=R/'GeometryViews';O.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH'
s.render.resolution_x=720;s.render.resolution_y=720;s.render.resolution_percentage=100
s.display.shading.light='STUDIO';s.display.shading.studiolight_rotate_z=math.radians(35)
s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=True
s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
s.display.shading.background_type='WORLD';s.world=bpy.data.worlds.new('ReviewWorld');s.world.color=(.09,.09,.09)
cam=bpy.data.cameras.new('Camera');co=bpy.data.objects.new('Camera',cam);s.collection.objects.link(co);s.camera=co;cam.type='ORTHO';cam.clip_end=1000;cam.ortho_scale=55
co.location=(95,-240,153);co.rotation_euler=(Vector((0,-2,132))-co.location).to_track_quat('-Z','Y').to_euler()
files=sorted((R/'BackViews').glob('*.json'))
if '--' in sys.argv:
 terms=sys.argv[sys.argv.index('--')+1:]
 files=[f for f in files if any(term in f.stem for term in terms)]
for f in files:
 data=json.loads(f.read_text());mesh=bpy.data.meshes.new(f.stem);mesh.from_pydata(data['positions'],[],data['triangles']);mesh.update()
 ob=bpy.data.objects.new(f.stem,mesh);s.collection.objects.link(ob)
 for name in data['materials']:
  mat=bpy.data.materials.new(str(name));mat.diffuse_color=(.1,.22,.42,1) if 'mage' in f.stem.lower() else (.51,.50,.47,1)
  if 'Hood' in str(name):mat.diffuse_color=(.12,.27,.48,1)
  mesh.materials.append(mat)
 for poly,slot in zip(mesh.polygons,data['triangle_materials']):poly.material_index=slot;poly.use_smooth=True
 s.render.filepath=str(O/(f.stem+'.png'));bpy.ops.render.render(write_still=True)
 bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(mesh)
print('KAITLIN_BACK_GEOMETRY_VIEWS',len(files),flush=True)
