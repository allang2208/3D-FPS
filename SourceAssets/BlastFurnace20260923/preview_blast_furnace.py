"""Authoring sanity render for the blast furnace (Blender only, headless).

    & blender.exe --background SourceAssets/BlastFurnace20260923/Authored/BlastFurnace.blend \
        --python SourceAssets/BlastFurnace20260923/preview_blast_furnace.py

This is NOT the user's visual acceptance and it starts nothing in UE. It is a
production self-check that catches a missing part or a collapsed proportion
before the mesh is handed over. Output goes to Authored/Preview/ (ignored by
git).
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(bpy.data.filepath).resolve().parent
OUT = HERE / 'Preview'
OUT.mkdir(parents=True, exist_ok=True)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x = 900
scene.render.resolution_y = 900
scene.render.film_transparent = False
scene.render.image_settings.file_format = 'PNG'
available = [v.identifier for v in scene.view_settings.bl_rna.properties['view_transform'].enum_items]
for preferred in ('AgX', 'Filmic', 'Standard'):
    if preferred in available:
        scene.view_settings.view_transform = preferred
        break
scene.view_settings.exposure = -1.1

world = bpy.data.worlds.new('PreviewWorld')
scene.world = world
world.use_nodes = True
background = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
background.inputs['Color'].default_value = (0.055, 0.06, 0.07, 1)
background.inputs['Strength'].default_value = 1.0


def area_light(name, location, energy, size, color=(1, 1, 1)):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    direction = Vector((0, 0, 1.1)) - Vector(location)
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    return obj


area_light('Key', (3.6, 3.0, 4.2), 900, 3.0, (1.0, 0.96, 0.90))
area_light('Fill', (-3.4, 2.6, 1.8), 320, 3.5, (0.85, 0.90, 1.0))
area_light('Rim', (-1.6, -3.8, 3.0), 480, 2.5, (1.0, 0.92, 0.82))

ground = bpy.data.meshes.new('Ground')
ground.from_pydata([(-14, -14, 0), (14, -14, 0), (14, 14, 0), (-14, 14, 0)], [], [(0, 1, 2, 3)])
ground.update()
ground_obj = bpy.data.objects.new('Ground', ground)
bpy.context.collection.objects.link(ground_obj)
ground_mat = bpy.data.materials.new('PreviewGround')
ground_mat.use_nodes = True
bsdf = next(n for n in ground_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
bsdf.inputs['Base Color'].default_value = (0.10, 0.10, 0.105, 1)
bsdf.inputs['Roughness'].default_value = 0.85
ground.materials.append(ground_mat)

camera_data = bpy.data.cameras.new('PreviewCamera')
camera_data.lens = 62
camera = bpy.data.objects.new('PreviewCamera', camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera

TARGET = Vector((0.0, 0.0, 1.10))
SHOTS = [
    ('01_front_tap', Vector((4.35, 0.30, 1.65)), TARGET, 62),
    ('02_three_quarter', Vector((3.25, 3.05, 1.95)), TARGET, 62),
    ('03_blast_side', Vector((0.35, 4.30, 1.75)), TARGET, 62),
    ('04_back_ashdoor', Vector((-3.40, -3.10, 1.85)), TARGET, 62),
    ('05_mouth_top', Vector((1.55, 1.35, 4.15)), Vector((0.0, 0.0, 1.85)), 62),
    ('06_forehearth_closeup', Vector((2.05, 1.35, 0.85)), Vector((0.22, 0.0, 0.32)), 85),
]

for name, position, target, lens in SHOTS:
    camera_data.lens = lens
    camera.location = position
    camera.rotation_euler = (target - position).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / (name + '.png'))
    bpy.ops.render.render(write_still=True)
    print('FURNACE_PREVIEW_SHOT', name, flush=True)

print('FURNACE_PREVIEW_DONE', str(OUT))
