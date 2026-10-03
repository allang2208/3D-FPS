"""Produce the actual SI mesh pictogram; this is UI production, not acceptance."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;P=O.parents[1];(O/'Icons').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'Blender/SICompensator_ExportReady.blend'))
bpy.context.preferences.filepaths.save_version=0
ob=bpy.data.objects['SM_PitViper2011_SICompensator']
for other in list(bpy.context.scene.objects):
    if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
ob.hide_set(False);ob.hide_render=False
sys.path.insert(0,str(P/'skills/ue5-weapon-workflow/scripts'))
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
apply_grayscale([ob]);scene=bpy.context.scene;neutral_output(scene)
center=sum((Vector(p) for p in ob.bound_box),Vector())/8
bpy.ops.object.camera_add(location=center+Vector((.095,.18,.080)));cam=bpy.context.object
cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.067;scene.camera=cam
for loc,energy,size in [((.04,.08,.15),.18,.13),((-.05,.09,.03),.13,.09),((.04,-.12,.09),.10,.1)]:
    bpy.ops.object.light_add(type='AREA',location=center+Vector(loc));lamp=bpy.context.object
    lamp.data.energy=energy;lamp.data.shape='DISK';lamp.data.size=size
    lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='CYCLES';scene.cycles.samples=48
scene.world.color=(.06,.06,.06);scene.render.film_transparent=True
scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.filepath=str(O/'Icons/SICompensator_Model_Gray.png')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'Icons/SICompensator_Icon_Editable.blend'))
bpy.ops.render.render(write_still=True)
(O/'icon_source.json').write_text(json.dumps({'model':str(O/'Blender/SICompensator_ExportReady.blend'),
   'output':scene.render.filepath,'purpose':'exclusive gunsmith pictogram from the actual model; muzzle forward left',
   'game_tested':False,'acceptance_rendered':False},indent=2),encoding='utf8')
print('PIT_VIPER_SI_COMPENSATOR_ICON_SOURCE_SAVED',flush=True)
