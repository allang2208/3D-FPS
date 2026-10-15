"""Production icon input: one representative head from the final paired module."""
import bpy,bmesh,json,runpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
(P/'IconSources').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'MeteorCore_Detailed_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
row=json.loads((P/'exports.json').read_text(encoding='utf-8'))['parts'][0]
obj=bpy.data.objects[row['mesh']]
for other in list(bpy.context.scene.objects):
    if other!=obj:bpy.data.objects.remove(other,do_unlink=True)
# The icon represents one side of the paired replacement, matching existing head icons.
bm=bmesh.new();bm.from_mesh(obj.data)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.co.x>0],context='VERTS')
bm.to_mesh(obj.data);bm.free();obj.data.update()
coords=[v.co for v in obj.data.vertices]
lo=Vector([min(v[j] for v in coords) for j in range(3)])
hi=Vector([max(v[j] for v in coords) for j in range(3)])
scale=1/max(hi-lo);obj.scale=(scale,)*3;obj.location=-(hi+lo)*.5*scale
helper=runpy.run_path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
helper['apply_grayscale']([obj])
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world.use_nodes=True
world=scene.world.node_tree.nodes.get('Background');world.inputs['Color'].default_value=(.35,.35,.35,1);world.inputs['Strength'].default_value=.45
scene.view_settings.view_transform='AgX';helper['neutral_output'](scene)
bpy.ops.object.camera_add(location=(-3.4,-5,0));camera=bpy.context.object
camera.rotation_euler=(-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=1.48;scene.camera=camera
for loc,power,size in [((-3,-4,3),450,3),((3,-2,1),220,2),((0,2,2),350,3)]:
    bpy.ops.object.light_add(type='AREA',location=loc);lamp=bpy.context.object
    lamp.data.energy=power;lamp.data.shape='DISK';lamp.data.size=size;lamp.rotation_euler=(-lamp.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(P/'IconSources/meteor_core.png');bpy.ops.render.render(write_still=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'MeteorCore_IconSource.blend'))
(P/'icon_source.json').write_text(json.dumps({'source':'MeteorCore_Detailed_Editable.blend','selection':'negative-X head only; runtime paired mesh unchanged',
 'camera':list(camera.location),'direction':'strike face left, connector right, +Z up','palette':'neutral-grayscale-20260927',
 'framing_reference':'SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png','file':'IconSources/meteor_core.png',
 'runtime_key':'ue_steel_warhammer_hammer_heads_meteor_core','tested':False},indent=2),encoding='utf-8')
print('METEOR_CORE_ICON_SOURCE_SAVED',flush=True)
