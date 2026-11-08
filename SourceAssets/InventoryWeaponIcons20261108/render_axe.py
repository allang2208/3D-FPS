"""Produce the portrait inventory artwork from the existing packed axe model."""
import json
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
SOURCE = PROJECT / 'SourceAssets/AxeImpactInventory20260919/axe_upright.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), use_scripts=False)
scene = bpy.context.scene
meshes = [obj for obj in scene.objects if obj.type == 'MESH' and not obj.hide_render]
points = [obj.matrix_world @ vertex.co for obj in meshes for vertex in obj.data.vertices]
lower = Vector(tuple(min(point[i] for point in points) for i in range(3)))
upper = Vector(tuple(max(point[i] for point in points) for i in range(3)))
center = (lower + upper) * .5
span = upper - lower

# Match tool_axe's 1 x 3 footprint without stretching the actual weapon.
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64
scene.cycles.use_denoising = True
scene.render.resolution_x = 512
scene.render.resolution_y = 1536
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.image_settings.color_depth = '8'
scene.view_settings.view_transform = 'AgX'
camera = scene.camera
camera.data.type = 'ORTHO'
camera.data.sensor_fit = 'VERTICAL'
camera.data.ortho_scale = max(span.z, span.x * 3.) / .91
camera.location = Vector((center.x, lower.y - 6., center.z))
camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()

ROOT.joinpath('Artwork').mkdir(exist_ok=True)
scene.render.filepath = str(ROOT / 'Artwork/axe.png')
# Only the active PBR material belongs to this output. The old FBX also left
# unused image datablocks whose original .fbm directory never existed.
for obj in meshes:
    for material in obj.data.materials:
        if material and material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image and not node.image.packed_file:
                    node.image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'Axe_Inventory_Studio.blend'))
bpy.ops.render.render(write_still=True)
(ROOT / 'axe-authoring.json').write_text(json.dumps({
    'source': str(SOURCE),
    'mesh_asset': '/Game/Items/ProductionTools/BattleAxe20260919/SM_BattleAxe',
    'dimensions': [512, 1536],
    'projection': 'orthographic side, upright, blade right',
    'dominant_axis_fill': .91,
    'geometry_and_pbr': 'existing packed source, unchanged',
    'runtime_tested': False,
}, indent=2), encoding='utf-8')
print('AXE_INVENTORY_ARTWORK_WRITTEN', scene.render.filepath, flush=True)
