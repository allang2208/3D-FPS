"""Manufacture the factory stock UI icon from its actual mesh, with a modeled common-style frame."""
import bpy,math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
with bpy.data.libraries.load(str(O/'FactoryStock.blend'),link=False) as (_,d):d.objects=['Super90_FactoryStock']
grip=d.objects[0];bpy.context.collection.objects.link(grip)
def mat(name,v,metal,rough):
 m=bpy.data.materials.new(name);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(v,v,v,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough;return m
silver=mat('Brushed steel frame',.35,.85,.33);dark=mat('Recessed charcoal backing',.022,.6,.43);edge=mat('Outer dark steel',.05,.85,.4);grey=mat('Factory polymer grayscale',.24,0,.52)
lo=Vector([min(v.co[i] for v in grip.data.vertices) for i in range(3)]);hi=Vector([max(v.co[i] for v in grip.data.vertices) for i in range(3)]);center=(lo+hi)*.5;scale=1.38/max(hi-lo)
# +Y (muzzle) faces left. Slightly oblique side view exposes the original mounting web.
rot=Matrix(((0,-1,0),(0,0,1),(-1,0,0))).to_4x4()@Matrix.Rotation(math.radians(-8),4,'Z')
grip.data.transform(Matrix.Translation((0,0,.17))@Matrix.Scale(scale,4)@rot@Matrix.Translation(-center));grip.data.materials.clear();grip.data.materials.append(grey)
for p in grip.data.polygons:p.material_index=0;p.use_smooth=True
def cube(name,loc,size,material,bevel):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material)
 b=o.modifiers.new('Machined bevel','BEVEL');b.width=bevel;b.segments=3;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL');return o
cube('Recessed back plate',(0,0,-.12),(1.92,1.92,.12),dark,.12)
for axis in (0,1):
 for sign in (-1,1):
  loc=[0,0,-.025];loc[axis]=sign*.91;size=[1.88,1.88,.14];size[axis]=.16
  cube('Silver bevel frame',loc,size,silver,.035)
  loc[axis]=sign*.985;cube('Outer charcoal edge',loc,[.035,1.79,.11] if axis==0 else [1.79,.035,.11],edge,.01)
bpy.ops.mesh.primitive_torus_add(major_radius=.796,minor_radius=.027,major_segments=160,minor_segments=12,location=(0,0,-.015));bpy.context.object.data.materials.append(silver)
for x in (-.825,.825):
 for y in (-.825,.825):
  cube('Corner bolt seat',(x,y,.005),(.23,.23,.12),edge,.047)
  bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=.059,location=(x,y,.092));bolt=bpy.context.object;bolt.scale.z=.5;bolt.data.materials.append(silver)
  for p in bolt.data.polygons:p.use_smooth=True
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.render.resolution_x=scene.render.resolution_y=768;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
scene.world=bpy.data.worlds.new('Icon neutral studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(1,1,1,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
camdata=bpy.data.cameras.new('IconCamera');cam=bpy.data.objects.new('IconCamera',camdata);scene.collection.objects.link(cam);cam.location=(0,0,4);cam.rotation_euler=(0,0,0);camdata.type='ORTHO';camdata.ortho_scale=2.06;scene.camera=cam
for loc,power,size in [((-2,3,4),280,3),((2,-1,3),110,2),((-1,-2,2),60,1.4)]:
 light=bpy.data.lights.new('Icon softbox','AREA');light.energy=power;light.size=size;ob=bpy.data.objects.new(light.name,light);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(O/'ue_super90_stock_false.png');bpy.ops.wm.save_as_mainfile(filepath=str(O/'FactoryStock_Icon.blend'));bpy.ops.render.render(write_still=True)
print('SUPER90_FACTORY_STOCK_ICON_AUTHORED')
