"""Produce icon source renders from the final meshes, not the concept painting."""
import bpy,json,runpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;(P/'IconSources').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'CommonHammerPommels_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
rows=json.loads((P/'exports.json').read_text(encoding='utf-8'))['parts']
objects=[bpy.data.objects[r['mesh']] for r in rows]
for obj in list(bpy.context.scene.objects):
    if obj not in objects:bpy.data.objects.remove(obj,do_unlink=True)
for obj in objects:
    obj.hide_render=True
    points=[v.co for v in obj.data.vertices];lo=Vector([min(v[j] for v in points) for j in range(3)]);hi=Vector([max(v[j] for v in points) for j in range(3)])
    scale=1/(hi.z-lo.z);obj.scale=(scale,)*3;obj.location=-(lo+hi)*.5*scale
helper=runpy.run_path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
helper['apply_grayscale'](objects)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world.use_nodes=True;world=scene.world.node_tree.nodes.get('Background');world.inputs['Color'].default_value=(.35,.35,.35,1);world.inputs['Strength'].default_value=.45
scene.view_settings.view_transform='AgX';helper['neutral_output'](scene)
bpy.ops.object.camera_add(location=(-1.8,-5,.05));camera=bpy.context.object;camera.rotation_euler=(-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=1.16;scene.camera=camera
for loc,power,size in [((-3,-4,3),450,3),((3,-2,1),220,2),((0,2,2),350,3)]:
    bpy.ops.object.light_add(type='AREA',location=loc);lamp=bpy.context.object;lamp.data.energy=power;lamp.data.shape='DISK';lamp.data.size=size
    lamp.rotation_euler=(-lamp.location).to_track_quat('-Z','Y').to_euler()
for row,obj in zip(rows,objects):
    obj.hide_render=False;scene.render.filepath=str(P/'IconSources'/(row['id']+'.png'));bpy.ops.render.render(write_still=True);obj.hide_render=True
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'CommonHammerPommels_IconSources.blend'))
(P/'icon_sources.json').write_text(json.dumps({'source':'CommonHammerPommels_Editable.blend','camera':list(camera.location),'axis':'+Z upright',
    'palette':'neutral-grayscale-20260927','framing_reference':'SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png',
    'images':[{'id':r['id'],'file':'IconSources/'+r['id']+'.png','runtime_key':'pommel_'+r['id']} for r in rows]},indent=2),encoding='utf-8')
print('COMMON_POMMEL_ICON_SOURCES_SAVED',flush=True)
