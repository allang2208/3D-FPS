"""Scoped ADS fault reproduction with separately coloured components."""
import bpy,numpy as np,math,sys
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
after='--after' in sys.argv
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.render.resolution_x=1440;sc.render.resolution_y=810;sc.render.resolution_percentage=100
sc.world=bpy.data.worlds.new('Background');sc.world.color=(.09,.09,.09)
sh=sc.display.shading;sh.light='STUDIO';sh.studio_light='paint.sl';sh.color_type='MATERIAL';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='WORLD'
for key in ['201','shirt','ue_field_gloves']:
 a=np.load(O/('shirt_fitted_projection.npz' if after and key=='shirt' else key+'_projection.npz'));p=a['points'].copy();p[:,1]*=-1
 faces=a['faces'];mids=a['material_ids'];names=a['material_names']
 if key=='201':
  keep=np.array(['Bare' not in str(names[i]) and 'Magazine' not in str(names[i]) for i in mids]);faces=faces[keep];mids=mids[keep]
 me=bpy.data.meshes.new(key);me.from_pydata(p.tolist(),[],faces.tolist());me.update()
 for n in names:
  m=bpy.data.materials.new(str(n));m.diffuse_color=(.10,.45,.62,1) if key=='shirt' else (.52,.28,.12,1) if 'gloves' in key else (.26,.28,.31,1);me.materials.append(m)
 for f,mi in zip(me.polygons,mids):f.material_index=int(mi);f.use_smooth=True
 ob=bpy.data.objects.new(key,me);sc.collection.objects.link(ob)
 cd=bpy.data.cameras.new('ADS camera');cd.type='PERSP';cd.lens=35;cd.sensor_fit='VERTICAL';cd.sensor_height=2*35*math.tan(math.radians(55/2));cd.clip_start=.1;cd.clip_end=500
 cam=bpy.data.objects.new('Camera',cd);sc.collection.objects.link(cam);cam.matrix_world=Matrix(((0,0,-1,0),(-1,0,0,0),(0,1,0,0),(0,0,0,1)));sc.camera=cam
sc.render.image_settings.file_format='PNG';sc.render.filepath=str(O/('ads_cloth_after.png' if after else 'ads_cloth_before.png'));bpy.ops.render.render(write_still=True)
