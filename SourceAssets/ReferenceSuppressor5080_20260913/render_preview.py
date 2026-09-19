"""User-requested pictures of the actual generated candidate; does not change the asset."""
import bpy
import json
import argparse
import sys
from mathutils import Vector, Matrix
from pathlib import Path

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, default=ROOT / 'seed_91353' / 'Suppressor_5080_Candidate_Editable.blend')
parser.add_argument('--outdir', type=Path, default=ROOT / 'seed_91353' / 'Preview')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
PREVIEW = args.outdir
PREVIEW.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(args.source))
scene = bpy.context.scene
objects = [o for o in scene.objects if o.type == 'MESH']
points = [o.matrix_world @ Vector(v) for o in objects for v in o.bound_box]
lo = Vector([min(p[i] for p in points) for i in range(3)])
hi = Vector([max(p[i] for p in points) for i in range(3)])
center = (hi + lo) * 0.5
dimensions = hi - lo
long_axis = max(range(3), key=lambda i: dimensions[i])
along = Vector([float(i == long_axis) for i in range(3)])
up = Vector((0, 0, 1)) if long_axis != 2 else Vector((0, 1, 0))
side = -along.cross(up).normalized()
span = max(dimensions)

scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.resolution_x = 1600
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX'
scene.view_settings.exposure = 0.5
world = bpy.data.worlds.new('Preview_Studio')
world.use_nodes = True
world.node_tree.nodes.clear()
background = world.node_tree.nodes.new('ShaderNodeBackground')
world_output = world.node_tree.nodes.new('ShaderNodeOutputWorld')
world.node_tree.links.new(background.outputs[0], world_output.inputs[0])
background.inputs['Color'].default_value = (0.11, 0.13, 0.16, 1)
background.inputs['Strength'].default_value = 0.6
scene.world = world

def area(name, direction, power, size):
    bpy.ops.object.light_add(type='AREA', location=center + direction * span)
    lamp = bpy.context.object
    lamp.name = name
    lamp.data.energy = power * span * span
    lamp.data.shape = 'DISK'
    lamp.data.size = size * span
    lamp.rotation_euler = (center - lamp.location).to_track_quat('-Z', 'Y').to_euler()

area('Preview_Key', side * 1.5 + up * 2.0 - along * 0.7, 380, 2.0)
area('Preview_Fill', side * 2.0 - up * 0.1 + along * 1.2, 160, 2.2)
area('Preview_Rim', -side * 1.3 + up * 1.1, 460, 1.8)

bpy.ops.object.camera_add()
camera = bpy.context.object
camera.name = 'Preview_Camera'
camera.data.type = 'ORTHO'
scene.camera = camera

def render(name, direction):
    forward = -direction.normalized()
    right = forward.cross(up).normalized()
    camera_up = right.cross(forward).normalized()
    camera.location = center + direction.normalized() * span * 3.0
    camera.rotation_euler = Matrix((right, camera_up, -forward)).transposed().to_euler()
    projected_x = [(p - center).dot(right) for p in points]
    projected_y = [(p - center).dot(camera_up) for p in points]
    aspect = scene.render.resolution_x / scene.render.resolution_y
    camera.data.ortho_scale = max(max(projected_x)-min(projected_x), (max(projected_y)-min(projected_y))*aspect) * 1.18
    scene.render.filepath = str(PREVIEW / (name + '.png'))
    bpy.ops.render.render(write_still=True)
    print('PREVIEW_SAVED ' + scene.render.filepath, flush=True)

render('side', side)
render('angle', side + along * 0.65 + up * 0.33)
(PREVIEW / 'receipt.json').write_text(json.dumps({
    'source':str(args.source),
    'type':'Actual generated model rendered in Blender',
    'images':['side.png','angle.png'],
    'mesh_edited':False,
    'source_materials_retained':True,
    'game_tested':False
}, indent=2), encoding='utf-8')
