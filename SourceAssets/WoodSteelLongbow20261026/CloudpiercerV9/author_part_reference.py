"""Actual Cloudpiercer production mesh, isolated solely for the framed icon input."""
from pathlib import Path
import bpy, json, math, sys
from mathutils import Matrix, Vector

P = Path(__file__).parent
SOURCE = P.parent / 'CloudpiercerV9/HighlandLongbow_Cloudpiercer_Production.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
body = bpy.data.objects['SK_HighlandLongbow_Cloudpiercer']
body.parent = None
body.modifiers.clear()
body.matrix_world = Matrix.Identity(4)
body.hide_set(False)
body.hide_render = False
for obj in list(bpy.data.objects):
    if obj != body:
        bpy.data.objects.remove(obj, do_unlink=True)
low = Vector(tuple(min(v.co[i] for v in body.data.vertices) for i in range(3)))
high = Vector(tuple(max(v.co[i] for v in body.data.vertices) for i in range(3)))
center = (low + high) * .5
scale = 1.65 / (high.z - low.z)
body.data.transform(Matrix.Scale(scale, 4) @ Matrix.Translation(-center))
sys.path.insert(0, 'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale, neutral_output
apply_grayscale([body])
neutral_output(scene)

def aim(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat('-Z', 'Y').to_euler()

bpy.ops.object.camera_add(location=(.55, -4, .02))
camera = bpy.context.object
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 1.90
aim(camera, (0, 0, 0))
scene.camera = camera
for name, location, power, size in [
    ('Large neutral key', (-1.5, -2, 2), 95, 2),
    ('Neutral edge fill', (1.6, -.8, .4), 45, 1.3),
    ('Neutral lower fill', (-1, -1, -1.7), 30, 1.5),
]:
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = power
    data.shape = 'DISK'
    data.size = size
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    aim(obj, (0, 0, 0))
scene.world = bpy.data.worlds.new('Cloudpiercer icon neutral world')
scene.world.use_nodes = True
background = next(n for n in scene.world.node_tree.nodes if n.type == 'BACKGROUND')
background.inputs['Color'].default_value = (.2, .2, .2, 1)
background.inputs['Strength'].default_value = .2
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x = scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.filepath = str(P / 'cloudpiercer_actual_part.png')
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'Cloudpiercer_Icon_Input.blend'))
bpy.ops.render.render(write_still=True)
(P / 'part-source.json').write_text(json.dumps({
    'production_source': str(SOURCE),
    'object': body.name,
    'runtime_mesh': '/Game/Weapons/WoodSteelLongbow20261026/CloudpiercerV9/SK_HighlandLongbow_Cloudpiercer',
    'orientation': 'Z up, view from -Y, 7.83 degrees toward +X, no 2D mirror',
    'frame_master': 'SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png',
    'resolution': [1024, 1024],
    'source_materials_copied_to_grayscale': True,
    'runtime_mesh_and_materials_changed': False,
    'output': str(P / 'cloudpiercer_actual_part.png'),
}, indent=2), encoding='utf-8')
print('CLOUDPIERCER_PART_REFERENCE_SAVED', flush=True)
