"""Create the actual inventory asset; this is not a gameplay/acceptance render."""
import bpy
from pathlib import Path
from mathutils import Vector

P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Zhanmadao_Fitted_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
weapon=bpy.data.objects['SM_Zhanmadao_Complete_V1']
# Inventory artwork keeps the actual material colors; modification icons use gray.
coords=[v.co for v in weapon.data.vertices]
lo=Vector(tuple(min(v[i] for v in coords) for i in range(3)));hi=Vector(tuple(max(v[i] for v in coords) for i in range(3)));center=(lo+hi)*.5
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=3
scene.render.resolution_x=512;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('InventoryLighting');scene.world.color=(.22,.22,.22)
bpy.ops.object.camera_add(location=center+Vector((0,-4,0)));camera=bpy.context.object
camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=(hi.z-lo.z)/.93;scene.camera=camera
for loc,power,size in [((-2,-3,3),480,3),((2,-2,.3),230,2),((.5,1,2),350,2)]:
    bpy.ops.object.light_add(type='AREA',location=center+Vector(loc));lamp=bpy.context.object;lamp.data.energy=power;lamp.data.size=size
    lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(P/'Export/ue_zhanmadao.png')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Zhanmadao_InventoryIcon_Editable.blend'))
bpy.ops.render.render(write_still=True)
print('ZHANMADAO_INVENTORY_ICON_SAVED',flush=True)
