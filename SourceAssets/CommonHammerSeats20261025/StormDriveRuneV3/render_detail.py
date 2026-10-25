import bpy,importlib.util
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'StormDriveTrimV2/TopInspectionScene.blend'))
for obj in list(bpy.context.scene.objects):
    if obj.type=='MESH':bpy.data.objects.remove(obj,do_unlink=True)
with bpy.data.libraries.load(str(P/'StormDriveSeats_Editable_V3.blend'),link=False) as (a,b):b.objects=['SM_SteelWarhammer_StormDrive_V3','SM_RuneboundWarhammer_StormDrive_V3']
for obj in b.objects:bpy.context.scene.collection.objects.link(obj);obj.hide_set(False);obj.hide_render=True
scene=bpy.context.scene;cam=scene.camera
scene.render.resolution_x=900;scene.render.resolution_y=1100
for obj,label,z,size in [(b.objects[0],'steel',.931,.102),(b.objects[1],'runebound',.917,.112)]:
    obj.hide_render=False;center=Vector((0,-.026,z));cam.location=(.020,-.34,z+.014)
    cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=size
    scene.render.filepath=str(P/('fine_rune_'+label+'.png'));bpy.ops.render.render(write_still=True);obj.hide_render=True
steel=b.objects[0];steel.hide_render=False
helper=Path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
spec=importlib.util.spec_from_file_location('gray',helper);gray=importlib.util.module_from_spec(spec);spec.loader.exec_module(gray)
gray.apply_grayscale([steel]);gray.neutral_output(scene)
center=Vector((0,0,.929));cam.location=(.12,-.36,1.001);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.17
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.film_transparent=True;scene.render.image_settings.color_mode='RGBA'
scene.render.filepath=str(P/'storm_drive_v3_actual_gray.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'StormDrive_V3_IconSource.blend'))
print('FINE_RUNE_DETAILS_RENDERED')
