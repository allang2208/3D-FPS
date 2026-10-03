"""Produce the requested inventory PNG from the same authored can and PBR maps."""
import json
from pathlib import Path

import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent
spec = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'SodaCan_Authored.blend'))
obj = bpy.data.objects['SM_SodaCan']
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 96
scene.cycles.use_denoising = True
scene.cycles.device = 'CPU'
scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.render.resolution_percentage = 50
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.film_transparent = True
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.view_settings.exposure = -.6
scene.world = bpy.data.worlds.new('SodaCanIconStudio')
scene.world.use_nodes = True
world_nodes = scene.world.node_tree.nodes
background = next((node for node in world_nodes if node.type == 'BACKGROUND'), None)
if background is None:
    background = world_nodes.new('ShaderNodeBackground')
    output = world_nodes.new('ShaderNodeOutputWorld')
    scene.world.node_tree.links.new(background.outputs['Background'], output.inputs['Surface'])
background.inputs['Color'].default_value = (.72, .75, .78, 1)
background.inputs['Strength'].default_value = .12
center = Vector((0, 0, spec['grip_height_cm'] / 100))

def aim(actor):
    actor.rotation_euler = (center - actor.location).to_track_quat('-Z', 'Y').to_euler()

for name, position, power, size in (
    ('SoftKey', (.30, -.40, .38), 7, .30),
    ('SoftFill', (-.28, -.20, .22), 3, .26),
    ('MetalRim', (.20, .32, .32), 5, .20),
):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = power
    data.shape = 'RECTANGLE'
    data.size = size
    data.size_y = .45
    actor = bpy.data.objects.new(name, data)
    scene.collection.objects.link(actor)
    actor.location = position
    aim(actor)
camera = bpy.data.objects.new('SodaCanInventoryCamera', bpy.data.cameras.new('SodaCanInventoryCamera'))
scene.collection.objects.link(camera)
camera.location = (.28, -.70, center.z + .17)
camera.data.type = 'ORTHO'
aim(camera)
bpy.context.view_layer.update()
view = camera.matrix_world.inverted()
projected = [view @ (obj.matrix_world @ v.co) for v in obj.data.vertices]
left, right = min(v.x for v in projected), max(v.x for v in projected)
bottom, top = min(v.y for v in projected), max(v.y for v in projected)
camera.data.ortho_scale = max(right - left, top - bottom) / .91
# Center the projected silhouette, rather than the unprojected bounds alone.
camera.location += camera.matrix_world.to_3x3() @ Vector(((left + right) * .5, (bottom + top) * .5, 0))
scene.camera = camera
scene.render.filepath = spec['icon']
Path(spec['icon']).parent.mkdir(parents=True, exist_ok=True)
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'SodaCan_InventoryIcon.blend'))
print('SODA_CAN_INVENTORY_ICON_SAVED ' + spec['icon'])
