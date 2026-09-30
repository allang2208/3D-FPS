"""One scoped ADS diagnostic view, from the current installed skin/aim data."""
import bpy,numpy as np,math,sys
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;complete='--complete' in sys.argv;a=np.load(O/('projected_complete.npz' if complete else 'projected.npz'))
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.render.resolution_x=1280;sc.render.resolution_y=720;sc.render.resolution_percentage=100
sc.world=bpy.data.worlds.new('Diagnostic background');sc.world.color=(.07,.07,.07);sh=sc.display.shading;sh.light='STUDIO';sh.studio_light='paint.sl';sh.color_type='MATERIAL';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='WORLD'
pts=a['points'].copy();pts[:,1]*=-1
me=bpy.data.meshes.new('Installed201ADS');me.from_pydata(pts.tolist(),[],a['faces'].tolist());me.update()
for i,name in enumerate(a['material_names']):
 m=bpy.data.materials.new(str(name))
 m.diffuse_color=(.6,.32,.20,1) if 'Bare' in name else (.8,.18,.05,1) if 'Reference' in name else (.25,.4,.53,1) if str(name).endswith('_34') else (.26,.28,.31,1)
 me.materials.append(m)
for p,mi in zip(me.polygons,a['material_ids']):p.material_index=int(mi);p.use_smooth=False
ob=bpy.data.objects.new('Current 201 - iron ADS geometry',me);sc.collection.objects.link(ob)
camdata=bpy.data.cameras.new('ADS 55 degree vertical');camdata.type='PERSP';camdata.lens=35;camdata.sensor_fit='VERTICAL';camdata.sensor_height=2*35*math.tan(math.radians(55/2));camdata.clip_start=1.;camdata.clip_end=500
cam=bpy.data.objects.new('Camera',camdata);sc.collection.objects.link(cam);cam.matrix_world=Matrix(((0,0,-1,0),(-1,0,0,0),(0,1,0,0),(0,0,0,1)));sc.camera=cam
sc.render.image_settings.file_format='PNG';sc.render.filepath=str(O/('ads_geometry_complete.png' if complete else 'ads_geometry_before.png'))
bpy.ops.render.render(write_still=True)
print('ADS31_DIAGNOSTIC_RENDERED',flush=True)
