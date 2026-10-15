"""Produce the inventory icon from the delivered mesh; no acceptance preview."""
import bpy, math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'SteelWarhammer_Editable.blend'))
hammer=bpy.data.objects['SM_SteelWarhammer'];rig=hammer.parent
hammer.data.transform(rig.data.bones['WPN_root'].matrix_local.inverted());hammer.parent=None;hammer.modifiers.clear()
for o in list(bpy.context.scene.objects):
    if o!=hammer:bpy.data.objects.remove(o,do_unlink=True)
coords=[v.co for v in hammer.data.vertices];center=Vector((0,0,(min(v.z for v in coords)+max(v.z for v in coords))*.5))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=512;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world.color=(.22,.22,.22)
bpy.ops.object.camera_add(location=center+Vector((0,-3,0)));camera=bpy.context.object
camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=1.27;scene.camera=camera
for loc,power,size in [((-1,-2,2),140,2),((1,-1,1),90,1.5),((0,1,1.8),150,1.4)]:
    bpy.ops.object.light_add(type='AREA',location=loc);lamp=bpy.context.object;lamp.data.energy=power;lamp.data.shape='DISK';lamp.data.size=size
    lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(P/'Export/ue_steel_warhammer.png')
bpy.ops.render.render(write_still=True)
