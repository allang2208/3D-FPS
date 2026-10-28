"""Render the three revised real blades as inputs to the standard framed menu icons."""
import bpy,json,math,runpy
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Kukri_Blade_SurfaceV2_Editable.blend'))
scene=bpy.context.scene;data=json.loads((P/'surfaces.json').read_text(encoding='utf-8'))
objects=[bpy.data.objects[e['object']] for e in data['variants']]
gray=runpy.run_path(str(P.parent/'KukriBladeVariants20261026/icon_grayscale.py'))
gray['apply_grayscale'](objects)
for obj in list(scene.objects):
    if obj not in objects:bpy.data.objects.remove(obj,do_unlink=True)
camera=bpy.data.objects.new('SurfaceV2_IconCamera',bpy.data.cameras.new('SurfaceV2_IconCamera'))
scene.collection.objects.link(camera);camera.location=(0,-4,0)
camera.rotation_euler=(Vector()-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=1.9;scene.camera=camera
scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND')
bg.inputs['Color'].default_value=(.25,.25,.25,1);bg.inputs['Strength'].default_value=.28
for name,location,energy,size in [('FrontSoftbox',(.6,-3,1),95,1.5),('TopStrip',(-1,-2,2),180,1.5),('EdgeFill',(1,-2,-1),70,2)]:
    lamp=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(lamp)
    lamp.location=location;lamp.rotation_euler=(-lamp.location).to_track_quat('-Z','Y').to_euler()
    lamp.data.energy=energy;lamp.data.size=size
scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.film_transparent=True
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
gray['neutral_output'](scene)
rotation=Matrix.Rotation(-math.pi/2,4,'Y')
for obj in objects:
    points=[rotation@Vector(c) for c in obj.bound_box];center=sum(points,Vector())/8
    span=max(max(v.x for v in points)-min(v.x for v in points),max(v.z for v in points)-min(v.z for v in points))
    scale=1.55/span
    obj.matrix_world=Matrix.Translation(-center*scale)@Matrix.Diagonal((scale,scale,scale,1))@rotation
for obj,entry in zip(objects,data['variants']):
    for other in objects:other.hide_render=other!=obj;other.hide_set(other!=obj)
    scene.render.filepath=entry['icon_input'];bpy.ops.render.render(write_still=True)
    print('KUKRI_SURFACE_V2_ICON_INPUT '+entry['id'],flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Kukri_Blade_SurfaceV2_Icons_Editable.blend'))
