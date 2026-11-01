"""Render the actual revised part for its production modification icon."""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
with bpy.data.libraries.load(str(P/'GuanLei_InlaidC7_Editable.blend'),link=False) as (a,b):
    b.objects=['SM_ThunderGodHammer_head_mount_guan_lei_seat']
obj=b.objects[0];bpy.context.collection.objects.link(obj);obj.hide_render=False;obj.hide_set(False)
apply_grayscale([obj])
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
neutral_output(scene)
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('Icon neutral studio');scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.13,.13,.13,1);bg.inputs[1].default_value=.3
vs=[v.co for v in obj.data.vertices];lo=Vector([min(v[i] for v in vs) for i in range(3)]);hi=Vector([max(v[i] for v in vs) for i in range(3)])
scale=1.25/max(hi-lo);obj.scale=(scale,)*3;obj.location=-(lo+hi)*.5*scale
bpy.ops.object.camera_add(location=(1.05,-4,.48));cam=bpy.context.object
cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=1.62;scene.camera=cam
for loc,power,size in [((-2,-3,3),450,3),((2,-2,1),300,2),((0,1,2),450,2)]:
    bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size
    o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(P/'GuanLeiC7_IconSource.png');bpy.ops.render.render(write_still=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'GuanLeiC7_IconSource.blend'))
(P/'icon_source_receipt.json').write_text(json.dumps({'production_icon_only':True,'mesh':obj.name,
    'source':str(P/'GuanLei_InlaidC7_Editable.blend'),'output':scene.render.filepath,'gameplay_tested':False},indent=2),encoding='utf-8')
