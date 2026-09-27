"""Produce the revised target-weight UI icon from its current editable mesh."""
import bpy
import json
import importlib.util
from pathlib import Path
from mathutils import Vector

OUT = Path(__file__).parent
ICONS = OUT / 'Icons'
ICONS.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'dw715_target_muzzle_weight_Editable.blend'))
bpy.context.preferences.filepaths.save_version = 0
auth = json.loads((OUT / 'authoring.json').read_text(encoding='utf-8'))
objects = {key: bpy.data.objects[key] for key in auth['parts']}
spec = importlib.util.spec_from_file_location('attachment_gray',
    str(OUT.parents[1] / 'skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py'))
gray = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gray)
gray.apply_grayscale(list(objects.values()))
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
preferences = bpy.context.preferences.addons['cycles'].preferences
try:
    preferences.compute_device_type = 'OPTIX'
    preferences.get_devices()
    for device in preferences.devices: device.use = device.type != 'CPU'
    if any(d.use for d in preferences.devices): scene.cycles.device = 'GPU'
except (RuntimeError, TypeError):
    scene.cycles.device = 'CPU'
scene.render.resolution_x = scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
gray.neutral_output(scene)
scene.world = bpy.data.worlds.new('UIIconWorld')
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.new('ShaderNodeBackground')
world_output = scene.world.node_tree.nodes.new('ShaderNodeOutputWorld')
background.inputs[0].default_value = (.28, .28, .28, 1)
background.inputs[1].default_value = .7
scene.world.node_tree.links.new(background.outputs[0], world_output.inputs['Surface'])
camera_data = bpy.data.cameras.new('UIIconCamera')
camera = bpy.data.objects.new('UIIconCamera', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = 'ORTHO'
lights = []
for name, loc, energy, size in [('Key', (.04, .09, .13), 9, .14),
                               ('Rim', (-.06, -.08, .10), 7, .10),
                               ('Fill', (.10, .04, -.025), 3, .12)]:
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.shape = 'DISK'
    data.size = size
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = loc
    light.rotation_euler = (-light.location).to_track_quat('-Z', 'Y').to_euler()
    lights.append(light)
result = {}
for key, ob in objects.items():
    for other in scene.objects:
        if other.type == 'MESH': other.hide_render = other != ob
    ob.hide_set(False)
    points = [v.co for v in ob.data.vertices]
    low = Vector([min(p[i] for p in points) for i in range(3)])
    high = Vector([max(p[i] for p in points) for i in range(3)])
    center = (low + high) * .5
    camera.location = center + Vector((.18, .8, 0))
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.ortho_scale = max((high.x-low.x)*1.08 + (high.y-low.y)*.23,
                                  high.z-low.z) * 1.22
    scene.render.filepath = str(ICONS / ('ue_dan_wesson715_muzzle_' + key + '.png'))
    bpy.ops.render.render(write_still=True)
    result[key] = {'file': scene.render.filepath, 'resolution': [1024, 1024],
                   'style': 'Neutral grayscale; transparent; +X muzzle faces left; horizontal camera',
                   'destination_when_published': str(OUT.parents[1] / 'Content/ColdSteelData/AttachmentIcons20260913' / Path(scene.render.filepath).name)}
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'DW715_TargetWeightV2_IconScene.blend'))
(OUT / 'icons.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('DW715_MUZZLE_ICONS_PRODUCED ' + str(len(result)), flush=True)
