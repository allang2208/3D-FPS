"""Requested crown inspection, from the repaired production meshes."""
import bpy,importlib.util
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'TopInspectionScene.blend'))
for obj in list(bpy.context.scene.objects):
    if obj.type=='MESH':bpy.data.objects.remove(obj,do_unlink=True)
with bpy.data.libraries.load(str(P/'StormDriveSeats_Editable_V2.blend'),link=False) as (a,b):
    b.objects=['SM_SteelWarhammer_StormDrive_V2','SM_RuneboundWarhammer_StormDrive_V2']
for obj in b.objects:bpy.context.scene.collection.objects.link(obj);obj.hide_set(False);obj.hide_render=True
scene=bpy.context.scene;cam=scene.camera
for obj,label,z in [(b.objects[0],'steel',.966),(b.objects[1],'runebound',.961)]:
    obj.hide_render=False;center=Vector((0,0,z));cam.location=(.12,-.30,z+.109)
    cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(P/('top_'+label+'_after.png'));bpy.ops.render.render(write_still=True);obj.hide_render=True
steel=b.objects[0];steel.hide_render=False
helper=Path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
spec=importlib.util.spec_from_file_location('gray',helper);gray=importlib.util.module_from_spec(spec);spec.loader.exec_module(gray)
gray.apply_grayscale([steel]);gray.neutral_output(scene)
center=Vector((0,0,.929));cam.location=(.12,-.36,1.001);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.17
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.film_transparent=True;scene.render.image_settings.color_mode='RGBA'
scene.render.filepath=str(P/'storm_drive_v2_actual_gray.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'StormDrive_V2_IconSource.blend'))
print('CROWN_DETAIL_AND_ICON_SOURCE_RENDERED',flush=True)
