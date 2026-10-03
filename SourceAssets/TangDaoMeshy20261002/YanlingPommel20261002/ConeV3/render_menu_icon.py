"""Produce the gray modification-card input from the actual V3 mesh."""
import bpy
from pathlib import Path
from mathutils import Vector,Matrix
from importlib.util import spec_from_file_location,module_from_spec
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'TangDao_YanlingConeV3_Editable.blend'))
obj=bpy.data.objects['SM_TangDao_Pommel_yanling_breaker_ConeV3_LOD0'];scene=bpy.context.scene
for x in scene.objects:
    if x.type=='MESH':x.hide_render=x!=obj
obj.hide_set(False)
spec=spec_from_file_location('icon_gray','C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
gray=module_from_spec(spec);spec.loader.exec_module(gray);gray.apply_grayscale([obj]);gray.neutral_output(scene)
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='OPTIX'
    if any(d.type=='OPTIX' for d in prefs.devices):scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('Cone modification card studio');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.25,.25,.25,1);bg.inputs['Strength'].default_value=.7
center=Vector((0,0,-.080))
cam=bpy.data.objects.new('Actual cone card camera',bpy.data.cameras.new('Actual cone card camera'));scene.collection.objects.link(cam);scene.camera=cam
cam.data.type='ORTHO';cam.data.clip_start=.001;cam.location=center+Vector((.24,-.8,.075))
direction=(center-cam.location).normalized();up=Vector((1,0,0));right=direction.cross(up).normalized();up=right.cross(direction).normalized()
cam.rotation_euler=Matrix((right,up,-direction)).transposed().to_euler();cam.data.ortho_scale=.228
for name,delta,energy,size in [('Key',(.16,-.35,.20),32,.35),('Fill',(-.18,-.28,-.12),12,.28),('Rim',(.12,.25,-.05),25,.24)]:
    light=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(light)
    light.location=center+Vector(delta);light.data.energy=energy;light.data.shape='DISK';light.data.size=size
    light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
scene.view_settings.exposure=-2.8;scene.render.filepath=str(P/'Icons/ue_tang_dao_pommel_yanling_breaker_source.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'TangDao_YanlingConeV3Icon_Editable.blend'))
print('YANLING_CONE_V3_ICON_SOURCE_SAVED',flush=True)
