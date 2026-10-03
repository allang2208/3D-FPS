"""Produce the exclusive modification icon from the actual exported guard."""
import bpy
from pathlib import Path
from mathutils import Vector,Matrix
from importlib.util import spec_from_file_location,module_from_spec
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'TangDao_PhoenixFeatherGuard_Editable.blend'))
obj=bpy.data.objects['SM_TangDao_Guard_phoenix_feather_LOD0'];scene=bpy.context.scene
for x in scene.objects:
    if x.type=='MESH':x.hide_render=x!=obj
obj.hide_set(False)
spec=spec_from_file_location('icon_gray','C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
gray=module_from_spec(spec);spec.loader.exec_module(gray)
gray.apply_grayscale([obj]);gray.neutral_output(scene)
# This guard has blackened metal recesses. Preserve that material contrast in
# the icon instead of applying the default polymer-to-silver brightness lift.
for slot in obj.material_slots:
    if 'Garnet' in slot.material.name:continue
    nt=slot.material.node_tree
    bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    lum=next(n for n in nt.nodes if n.type=='RGBTOBW' and n.inputs[0].is_linked)
    remap=nt.nodes.new('ShaderNodeMapRange');remap.inputs['From Min'].default_value=0
    remap.inputs['From Max'].default_value=.55;remap.inputs['To Min'].default_value=.012;remap.inputs['To Max'].default_value=.52
    nt.links.new(lum.outputs[0],remap.inputs['Value']);nt.links.new(remap.outputs[0],bs.inputs['Base Color'])
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='OPTIX'
    if any(d.type=='OPTIX' for d in prefs.devices):scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('Xuan Cloud Guard icon studio');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.25,.25,.25,1);bg.inputs['Strength'].default_value=.7
center=Vector((.020,0,-.008))
cam=bpy.data.objects.new('Actual guard icon camera',bpy.data.cameras.new('Actual guard icon camera'))
scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO';cam.data.clip_start=.001
# Small oblique angle reveals real raised rims, pierced wall thickness and collar.
cam.location=center+Vector((.32,-.12,.85));direction=(center-cam.location).normalized();up=Vector((0,1,0));right=direction.cross(up).normalized();up=right.cross(direction).normalized();cam.rotation_euler=Matrix((right,up,-direction)).transposed().to_euler();cam.data.ortho_scale=.235
for name,delta,energy,size in [('Key',(-.2,.26,.38),38,.32),('Fill',(.24,.1,.2),14,.26),('Rim',(.1,-.26,-.12),25,.24)]:
    light=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(light)
    light.location=center+Vector(delta);light.data.energy=energy;light.data.shape='DISK';light.data.size=size
    light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
scene.view_settings.exposure=-3.15
scene.render.filepath=str(P/'Icons/ue_tang_dao_guard_phoenix_feather_source.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'TangDao_PhoenixFeatherGuardIcon_Editable.blend'))
print('PHOENIX_FEATHER_GUARD_ICON_SOURCE_SAVED',flush=True)
