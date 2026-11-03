"""Production icon authoring, never starts the game or renders an acceptance scene."""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
source=P/'JiLei_V15_Editable.blend'
if source.exists():
    with bpy.data.libraries.load(str(source),link=False) as(a,b):b.objects=['SM_ThunderGodHammer_head_mount_ji_lei_seat_V15']
    obj=b.objects[0];bpy.context.collection.objects.link(obj);obj.hide_render=False;obj.hide_set(False)
else:
    bpy.ops.import_scene.gltf(filepath=str(P/'Original/Meshy_AI_Nordic_Aegis_Shield_1101101638_texture.glb'))
    obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
apply_grayscale([obj])
vs=[obj.matrix_world@v.co for v in obj.data.vertices]
lo=Vector([min(v[i] for v in vs) for i in range(3)]);hi=Vector([max(v[i] for v in vs) for i in range(3)])
scale=1.25/max(hi-lo);obj.scale=(scale,)*3;obj.location=-(lo+hi)*.5*scale
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=8
neutral_output(scene)
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('Neutral icon studio');scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.12,.12,.12,1);bg.inputs[1].default_value=.25
bpy.ops.object.camera_add(location=(1.10,-4.1,.65));cam=bpy.context.object;cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=1.62;scene.camera=cam
for loc,power,size in [((-2,-3,3),230,3),((2,-2,1),110,2),((0,1,2),220,2)]:
    bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.size=size;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
(P/'Icon').mkdir(exist_ok=True)
scene.render.filepath=str(P/'Icon/ji_lei_seat_source.png')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'Icon/JiLei_Icon.blend'))
bpy.ops.render.render(write_still=True)
print('JILEI_PRODUCTION_ICON_SAVED',flush=True)
