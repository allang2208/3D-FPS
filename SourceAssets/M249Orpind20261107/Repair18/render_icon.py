"""Render the real 45-round shell in a clean scene for the existing icon frame."""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
r=Path(__file__).resolve().parent;source=r.parent/'Repair17';(r/'Icons').mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(source/'Exports/SM_m249_side_mag_45.blend'),link=False) as (src,dst):dst.objects=['SM_m249_side_mag_45']
ob=dst.objects[0];bpy.context.collection.objects.link(ob);ob.hide_render=False;ob.hide_set(False)
cfg=json.loads((source/'model_recipe.json').read_text());flip=np.diag([100,-100,100,1]);back=np.diag([.01,-.01,.01,1])
ob.matrix_world=Matrix((back@np.linalg.inv(np.array(cfg['donor_mag_to_root']))@np.array(cfg['idle_mag_frame'])@flip).tolist())
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-1.2;scene.view_settings.gamma=1
material=bpy.data.materials.new('M249 icon grey polymer');material.use_nodes=True
n=material.node_tree.nodes;l=material.node_tree.links;bs=n.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.29,.29,.29,1);bs.inputs['Roughness'].default_value=.5;bs.inputs['Metallic'].default_value=.12
coord=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=950;noise.inputs['Detail'].default_value=2
l.new(coord.outputs['Object'],noise.inputs['Vector']);bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16;bump.inputs['Distance'].default_value=.00007;l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bs.inputs['Normal'])
ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.17,.17,.17,1);ramp.color_ramp.elements[1].color=(.32,.32,.32,1);l.new(noise.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs['Color'],bs.inputs['Base Color'])
ob.data.materials.clear();ob.data.materials.append(material)
for slot in ob.material_slots:slot.link='DATA';slot.material=material
for face in ob.data.polygons:face.material_index=0
scene.world=bpy.data.worlds.new('Neutral catalog studio');scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.19,.19,.19,1);bg.inputs[1].default_value=.35
points=[ob.matrix_world@v.co for v in ob.data.vertices];center=(Vector(tuple(min(p[i] for p in points) for i in range(3)))+Vector(tuple(max(p[i] for p in points) for i in range(3))))*.5
data=bpy.data.cameras.new('Profile camera');cam=bpy.data.objects.new('Profile camera',data);scene.collection.objects.link(cam);scene.camera=cam;data.type='ORTHO'
direction=Vector((1,.07,0)).normalized();cam.location=center+direction;cam.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
inv=cam.rotation_euler.to_matrix().transposed();q=[inv@(p-center) for p in points];data.ortho_scale=max(max(p.x for p in q)-min(p.x for p in q),max(p.y for p in q)-min(p.y for p in q))*1.16
for name,offset,power,size in [('Key',(.65,-.45,.65),36,.52),('Fill',(.55,.50,.15),10,.6),('Rim',(-.1,.5,.5),30,.45)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size;obj=bpy.data.objects.new(name,light);scene.collection.objects.link(obj);obj.location=center+Vector(offset);obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(r/'Icons/M249_45_Model.png');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(r/'M249_45_Icon_Studio.blend'));bpy.ops.render.render(write_still=True)
print('M249_45_REAL_MODEL_ICON_RENDERED',flush=True)
