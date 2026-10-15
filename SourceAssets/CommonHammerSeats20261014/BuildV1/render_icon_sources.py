"""Production icon source images from the exported seat authoring meshes."""
import bpy,json,runpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'CommonHammerSeats_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
rows=json.loads((P/'exports.json').read_text(encoding='utf-8'))['parts']
modules=[bpy.data.objects[row['mesh']] for row in rows]
for obj in list(bpy.context.scene.objects):
    if obj not in modules:bpy.data.objects.remove(obj,do_unlink=True)
for obj in modules:
    obj.hide_set(False);obj.hide_render=True
    coords=[v.co for v in obj.data.vertices]
    lo=Vector(tuple(min(v[i] for v in coords) for i in range(3)));hi=Vector(tuple(max(v[i] for v in coords) for i in range(3)))
    scale=1/max(hi-lo);obj.scale=(scale,)*3;obj.location=-(lo+hi)*.5*scale
helper=runpy.run_path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
helper['apply_grayscale'](modules)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world.use_nodes=True;world=scene.world.node_tree.nodes.get('Background')
world.inputs['Color'].default_value=(.35,.35,.35,1);world.inputs['Strength'].default_value=.45
scene.view_settings.view_transform='AgX';helper['neutral_output'](scene)
bpy.ops.object.camera_add(location=(-2.3,-5,0));cam=bpy.context.object
cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=1.4;scene.camera=cam
for loc,power,size in [((-3,-4,3),450,4),((3,-2,1),280,3),((0,2,2),400,3)]:
    bpy.ops.object.light_add(type='AREA',location=loc);lamp=bpy.context.object
    lamp.data.energy=power;lamp.data.shape='DISK';lamp.data.size=size
    lamp.rotation_euler=(-lamp.location).to_track_quat('-Z','Y').to_euler()
for row,obj in zip(rows,modules):
    obj.hide_render=False;scene.render.filepath=str(P/'IconSources'/(row['id']+'.png'))
    bpy.ops.render.render(write_still=True);obj.hide_render=True
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'CommonHammerSeats_IconSources.blend'))
(P/'icon_sources.json').write_text(json.dumps({'camera':[-2.3,-5,0],'up':'+Z','resolution':[1024,1024],
    'palette':'neutral-grayscale-20260927','parts':[{'id':r['id'],'object':r['mesh'],'source':'CommonHammerSeats_Editable.blend',
    'runtime_key':'head_mount_'+r['id'],'image':'IconSources/'+r['id']+'.png'} for r in rows]},indent=2),encoding='utf-8')
