"""Production inventory icon input, from the actual saved model."""
import bpy,importlib.util,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'StormDriveSeats_Editable.blend'))
obj=bpy.data.objects['SM_SteelWarhammer_StormDrive_V1']
for other in bpy.context.scene.objects:other.hide_render=other!=obj
obj.hide_set(False)
helper=Path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
spec=importlib.util.spec_from_file_location('icon_gray',helper);gray=importlib.util.module_from_spec(spec);spec.loader.exec_module(gray)
gray.apply_grayscale([obj]);scene=bpy.context.scene;gray.neutral_output(scene)
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.render.threads_mode='FIXED';scene.render.threads=8
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100;scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
center=Vector((0,0,.929))
bpy.ops.object.camera_add(location=(.12,-.36,1.001));cam=bpy.context.object;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.17;scene.camera=cam
for loc,power,size in (((-.14,-.17,1.11),5,.17),((.15,-.07,.98),3,.12),((0,.13,1.06),7,.12)):
    bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=power;light.data.size=size;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(P/'storm_drive_actual_gray.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'StormDrive_IconSource.blend'))
