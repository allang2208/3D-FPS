"""Produce the new modification's UI artwork from its actual authored mesh."""
import bpy, json
from pathlib import Path
from mathutils import Vector, Matrix
from importlib.util import spec_from_file_location, module_from_spec
P = Path(__file__).resolve().parent
ROOT = P.parents[2]
bpy.ops.wm.open_mainfile(filepath=str(P / 'TangDao_YanlingBlade_Editable.blend'))
bpy.context.preferences.filepaths.save_version = 0
obj = bpy.data.objects['SM_TangDao_Blade_yanling_edge_LOD0']
obj.hide_set(False)
for other in bpy.context.scene.objects:
    if other.type == 'MESH':
        other.hide_render = other != obj
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    available = [d for d in prefs.devices if d.type == 'OPTIX']
    for d in prefs.devices:
        d.use = d in available
    if available:
        scene.cycles.device = 'GPU'
except Exception:
    pass
spec = spec_from_file_location('icon_gray', str(ROOT / 'skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py'))
gray = module_from_spec(spec)
spec.loader.exec_module(gray)
gray.apply_grayscale([obj])
gray.neutral_output(scene)
scene.render.resolution_x = scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.world = bpy.data.worlds.new('Yanling neutral icon studio')
scene.world.use_nodes = True
background = next(n for n in scene.world.node_tree.nodes if n.type == 'BACKGROUND')
background.inputs['Color'].default_value = (.2, .2, .2, 1)
background.inputs['Strength'].default_value = .65
points = [Vector(p) for p in obj.bound_box]
center = sum(points, Vector()) / 8
camera = bpy.data.objects.new('Production icon camera', bpy.data.cameras.new('Production icon camera'))
scene.collection.objects.link(camera)
scene.camera = camera
camera.data.type = 'ORTHO'
camera.data.clip_start = .001
camera.rotation_euler = Matrix(((0, 1, 0), (0, 0, -1), (-1, 0, 0))).to_euler()
camera.location = center + Vector((0, -1.5, 0))
camera.data.ortho_scale = (max(p.z for p in points) - min(p.z for p in points)) / .77
for name, delta, energy, size in [('Key', (.38, -.60, .35), 95, .75), ('Fill', (-.32, -.42, -.15), 45, .65), ('Rim', (.12, .28, .30), 65, .5)]:
    lamp = bpy.data.objects.new(name, bpy.data.lights.new(name, 'AREA'))
    scene.collection.objects.link(lamp)
    lamp.data.energy = energy
    lamp.data.shape = 'DISK'
    lamp.data.size = size
    lamp.location = center + Vector(delta)
    lamp.rotation_euler = (center - lamp.location).to_track_quat('-Z', 'Y').to_euler()
scene.view_settings.exposure = -2.8
output = P / 'Icons'
output.mkdir(exist_ok=True)
scene.render.filepath = str(output / 'ue_tang_dao_blade_1_yanling_edge_source.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'TangDao_YanlingIcon_Editable.blend'))
print('YANLING_PRODUCTION_ICON_SAVED', flush=True)
