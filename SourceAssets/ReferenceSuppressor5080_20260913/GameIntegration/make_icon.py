"""Produce the gunsmith option's shipped icon from its game mesh, without changing the source."""
import bpy
import math
import shutil
from pathlib import Path
from mathutils import Vector, Matrix

O = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O / 'TacticalSuppressor_FourWeapons_Editable.blend'))
s = bpy.context.scene
asset = bpy.data.objects['SM_TacticalSuppressor_M4']
for ob in s.objects:
    if ob.type in {'MESH', 'LIGHT'}:
        ob.hide_render = ob != asset
asset.hide_set(False)
points = [asset.matrix_world @ Vector(p) for p in asset.bound_box]
center = sum(points, Vector()) / len(points)
span = max(max(p[i] for p in points) - min(p[i] for p in points) for i in range(3))
s.render.engine = 'CYCLES'
s.cycles.samples = 32
s.cycles.use_denoising = True
s.render.resolution_x = 512
s.render.resolution_y = 512
s.render.resolution_percentage = 100
s.render.image_settings.file_format = 'PNG'
s.render.image_settings.color_mode = 'RGB'
s.render.film_transparent = False
s.view_settings.view_transform = 'AgX'
s.view_settings.exposure = .65
world = bpy.data.worlds.new('GunsmithIconStudio')
world.use_nodes = True
world.node_tree.nodes.clear()
background = world.node_tree.nodes.new('ShaderNodeBackground')
world_output = world.node_tree.nodes.new('ShaderNodeOutputWorld')
world.node_tree.links.new(background.outputs[0], world_output.inputs[0])
background.inputs['Color'].default_value = (.018, .022, .029, 1)
background.inputs['Strength'].default_value = .45
s.world = world

def light(name, direction, power, size):
    bpy.ops.object.light_add(type='AREA', location=center + Vector(direction) * span)
    ob = bpy.context.object
    ob.name = name
    ob.data.energy = power * span * span
    ob.data.size = size * span
    ob.rotation_euler = (center - ob.location).to_track_quat('-Z', 'Y').to_euler()

light('Icon_Key', (1.5, -.8, 2), 460, 1.8)
light('Icon_Fill', (2, 1.4, .1), 180, 2)
light('Icon_Rim', (-1.1, -.2, 1.2), 520, 1.6)
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.name = 'GunsmithIconCamera'
camera.data.type = 'ORTHO'
direction = Vector((1, .5, .28)).normalized()
forward = -direction
right0 = forward.cross(Vector((0, 0, 1))).normalized()
up0 = right0.cross(forward).normalized()
roll = math.radians(36)
right = right0 * math.cos(roll) + up0 * math.sin(roll)
up = -right0 * math.sin(roll) + up0 * math.cos(roll)
camera.location = center + direction * span * 3
camera.rotation_euler = Matrix((right, up, -forward)).transposed().to_euler()
px = [(p - center).dot(right) for p in points]
py = [(p - center).dot(up) for p in points]
camera.data.ortho_scale = max(max(px) - min(px), max(py) - min(py)) * 1.15
s.camera = camera
icon = O / 'muzzle_tactical_suppressor.png'
s.render.filepath = str(icon)
bpy.ops.render.render(write_still=True)
destination = O.parents[2] / 'Content/ColdSteelData/AttachmentIcons20260913' / icon.name
destination.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(icon, destination)
print('TACTICAL_ICON_CREATED ' + str(destination), flush=True)
