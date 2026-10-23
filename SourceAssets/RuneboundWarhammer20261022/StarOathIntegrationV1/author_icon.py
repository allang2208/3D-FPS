"""Render the actual final module as production input for its standard framed icon."""
import bpy
import importlib.util
import json
from pathlib import Path
from mathutils import Vector

P=Path(__file__).resolve().parent
SOURCE=P.parent/'StarOathHammerHeadV1/StarOathHammerHead_Assembled_PBR.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version=0
part=bpy.data.objects['SM_RuneboundWarhammer_StarOathHammerHeads_V1']
for obj in list(bpy.context.scene.objects):
    if obj!=part:
        bpy.data.objects.remove(obj,do_unlink=True)
part.location=(0,0,0)
part.hide_set(False)
part.hide_render=False
helper=Path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
spec=importlib.util.spec_from_file_location('icon_gray',helper)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.apply_grayscale([part])
scene=bpy.context.scene
module.neutral_output(scene)
for mat in part.data.materials:
    for node in mat.node_tree.nodes:
        if node.type=='BSDF_PRINCIPLED':
            strength=node.inputs.get('Emission Strength')
            if strength:
                for link in list(strength.links):
                    mat.node_tree.links.remove(link)
                strength.default_value=0
scene.render.engine='CYCLES'
scene.cycles.samples=32
scene.cycles.device='CPU'
scene.render.threads_mode='FIXED'
scene.render.threads=4
scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024
scene.render.resolution_percentage=100
scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGBA'
scene.world.color=(.15,.15,.15)
bpy.ops.object.camera_add(location=(0,-.95,.07))
camera=bpy.context.object
camera.rotation_euler=(-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO'
camera.data.ortho_scale=.43
scene.camera=camera
for location,power,size in (((-.35,-.45,.48),14,.45),((.4,-.25,.15),10,.32),((0,.25,.35),18,.35)):
    bpy.ops.object.light_add(type='AREA',location=location)
    light=bpy.context.object
    light.data.energy=power
    light.data.shape='DISK'
    light.data.size=size
    light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(P/'star_oath_actual_module_gray.png')
bpy.ops.render.render(write_still=True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'StarOath_ProductionIcon_Editable.blend'))
(P/'icon_input_receipt.json').write_text(json.dumps({'source':str(SOURCE),'mesh':part.name,
    'image':scene.render.filepath,'purpose':'production attachment icon input, not an acceptance render',
    'orientation':'installed horizontal X axis, Z up, front with small elevation',
    'resolution':[1024,1024],'grayscale':True,'frame':'generated separately from the approved standard'},indent=2),encoding='utf-8')
