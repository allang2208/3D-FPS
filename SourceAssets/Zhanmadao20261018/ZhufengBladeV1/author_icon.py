"""Render the authored blade as the source for the standard grayscale framed icon."""
import bpy,math,runpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Zhufeng_Blade_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
blade=bpy.data.objects['SM_Zhanmadao_Blade_zhufeng_V1_LOD0']
for obj in bpy.data.objects:obj.hide_render=obj!=blade
blade.parent=None;blade.rotation_euler[1]=math.pi/2
helper=runpy.run_path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
helper['apply_grayscale']([blade])
S=bpy.context.scene;helper['neutral_output'](S)
bpy.context.view_layer.update()
points=[blade.matrix_world@Vector(v) for v in blade.bound_box]
lo=Vector(tuple(min(v[i] for v in points) for i in range(3)));hi=Vector(tuple(max(v[i] for v in points) for i in range(3)));center=(lo+hi)*.5
S.render.engine='CYCLES';S.cycles.samples=32;S.cycles.use_denoising=True;S.render.threads_mode='FIXED';S.render.threads=3
S.render.resolution_x=1024;S.render.resolution_y=1024;S.render.resolution_percentage=100
S.render.film_transparent=True;S.render.image_settings.file_format='PNG';S.render.image_settings.color_mode='RGBA'
S.world=bpy.data.worlds.new('ZhufengIconLight');S.world.color=(.06,.06,.06)
S.view_settings.exposure=-1.3
bpy.ops.object.camera_add(location=center+Vector((0,4,.12)));camera=bpy.context.object
camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=(hi.x-lo.x)/.88;S.camera=camera
for loc,power,size in [((1.2,2.5,2),440,2.5),((-1,1,-.5),180,2),((0,-1,1),260,1.5)]:
    bpy.ops.object.light_add(type='AREA',location=center+Vector(loc));lamp=bpy.context.object;lamp.data.energy=power;lamp.data.size=size
    lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
S.render.filepath=str(P/'Export/Zhufeng_Icon_Subject.png')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Zhufeng_Icon_Editable.blend'))
bpy.ops.render.render(write_still=True)
print('ZHUFENG_ICON_SUBJECT_SAVED',flush=True)
