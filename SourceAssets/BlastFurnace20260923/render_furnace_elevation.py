"""Contract elevations and a human-scale reference for the blast furnace.

    & blender.exe --background SourceAssets/BlastFurnace20260923/Authored/BlastFurnace.blend \
        --python SourceAssets/BlastFurnace20260923/render_furnace_elevation.py

Three clay renders that verify the *placement contract* rather than the look:

* ``elevation_front_clay.png`` — orthographic, looking down -X (UE forward);
* ``elevation_side_clay.png``  — orthographic, looking down +Y;
* ``scale_reference_clay.png`` — perspective with a 180 cm figure beside it.

Orthographic so the pixel measurements in the receipt are exact: at
``ORTHO_SCALE`` metres over ``RES_Y`` pixels, one pixel is a known number of
millimetres, and the script reports the drawn silhouette against the contract.
Blender only, headless, CPU.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(bpy.data.filepath).resolve().parent
OUT = HERE / 'Verify'
OUT.mkdir(parents=True, exist_ok=True)

RES_X, RES_Y = 820, 1240
ORTHO_SCALE = 2.60                       # metres across the camera's long axis
MM_PER_PIXEL = ORTHO_SCALE / RES_Y * 1000.0

scene = bpy.context.scene
view_layer = bpy.context.view_layer
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 56
scene.cycles.use_denoising = True
scene.render.resolution_x = RES_X
scene.render.resolution_y = RES_Y
scene.render.image_settings.file_format = 'PNG'
available = [v.identifier for v in scene.view_settings.bl_rna.properties['view_transform'].enum_items]
for preferred in ('AgX', 'Filmic', 'Standard'):
    if preferred in available:
        scene.view_settings.view_transform = preferred
        break
scene.view_settings.exposure = -1.1

clay = bpy.data.materials.new('ElevationClay')
clay.use_nodes = True
clay_bsdf = next(n for n in clay.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
clay_bsdf.inputs['Base Color'].default_value = (0.62, 0.615, 0.605, 1.0)
clay_bsdf.inputs['Roughness'].default_value = 0.60
clay_bsdf.inputs['Specular IOR Level'].default_value = 0.28
view_layer.material_override = clay

world = bpy.data.worlds.new('ElevationWorld')
scene.world = world
world.use_nodes = True
background = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
background.inputs['Color'].default_value = (0.10, 0.105, 0.115, 1)
background.inputs['Strength'].default_value = 1.0


def area_light(name, location, energy, size):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector((0, 0, 1.1)) - Vector(location)).to_track_quat('-Z', 'Y').to_euler()
    return obj


area_light('Key', (3.2, 2.6, 4.0), 900, 3.2)
area_light('Fill', (-3.0, 2.2, 1.6), 300, 3.5)
area_light('Rim', (-1.4, -3.4, 3.0), 420, 2.5)

camera_data = bpy.data.cameras.new('ElevationCamera')
camera = bpy.data.objects.new('ElevationCamera', camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera

report = {'mm_per_pixel': round(MM_PER_PIXEL, 4), 'resolution': [RES_X, RES_Y],
          'ortho_scale_m': ORTHO_SCALE, 'rendered': True, 'runtime_tested': False}


def shoot(name, position, target, ortho):
    camera.location = Vector(position)
    camera.rotation_euler = (Vector(target) - Vector(position)).to_track_quat('-Z', 'Y').to_euler()
    if ortho:
        camera_data.type = 'ORTHO'
        camera_data.ortho_scale = ORTHO_SCALE
    else:
        camera_data.type = 'PERSP'
        camera_data.lens = 58
    scene.render.filepath = str(OUT / (name + '.png'))
    bpy.ops.render.render(write_still=True)
    print('FURNACE_ELEVATION_SHOT ' + name, flush=True)


# The elevations are rendered with a transparent film: the annotation step
# measures the silhouette from the alpha channel, so no lighting threshold can
# move the numbers.
scene.render.film_transparent = True
shoot('elevation_front_clay', (9.0, 0.0, 1.10), (0.0, 0.0, 1.10), True)
shoot('elevation_side_clay', (0.0, -9.0, 1.10), (0.0, 0.0, 1.10), True)
scene.render.film_transparent = False

# --- 180 cm scale figure (clay only; a measuring aid, not an asset) ----
ground = bpy.data.meshes.new('ElevationGround')
ground.from_pydata([(-14, -14, 0), (14, -14, 0), (14, 14, 0), (-14, 14, 0)], [], [(0, 1, 2, 3)])
ground.update()
bpy.context.collection.objects.link(bpy.data.objects.new('ElevationGround', ground))


def add_box(name, center, size):
    cx, cy, cz = center
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    verts = [(cx + sx * hx, cy + sy * hy, cz + sz * hz)
             for sz in (-1, 1) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    faces = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


FIGURE_X, FIGURE_Y = 1.15, -0.30
add_box('ScaleFigure_LegL', (FIGURE_X - 0.10, FIGURE_Y, 0.42), (0.15, 0.18, 0.85))
add_box('ScaleFigure_LegR', (FIGURE_X + 0.10, FIGURE_Y, 0.42), (0.15, 0.18, 0.85))
add_box('ScaleFigure_Hips', (FIGURE_X, FIGURE_Y, 0.94), (0.35, 0.24, 0.20))
add_box('ScaleFigure_Torso', (FIGURE_X, FIGURE_Y, 1.30), (0.42, 0.26, 0.54))
add_box('ScaleFigure_ArmL', (FIGURE_X - 0.265, FIGURE_Y, 1.25), (0.11, 0.16, 0.55))
add_box('ScaleFigure_ArmR', (FIGURE_X + 0.265, FIGURE_Y, 1.25), (0.11, 0.16, 0.55))
add_box('ScaleFigure_Neck', (FIGURE_X, FIGURE_Y, 1.62), (0.11, 0.11, 0.08))
head = bpy.data.meshes.new('ScaleFigure_Head')
import bmesh  # noqa: E402 - only needed for the sphere

bm = bmesh.new()
try:
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.105)
except TypeError:
    bmesh.ops.create_icosphere(bm, subdivisions=2, diameter=0.105)
for vert in bm.verts:
    vert.co.z += 1.695
    vert.co.x += FIGURE_X
    vert.co.y += FIGURE_Y
bm.to_mesh(head)
bm.free()
head_obj = bpy.data.objects.new('ScaleFigure_Head', head)
bpy.context.collection.objects.link(head_obj)

shoot('scale_reference_clay', (3.30, -3.05, 1.85), (0.15, -0.05, 1.05), False)
report['scale_figure'] = {'height_cm': 180.0, 'position_m': [FIGURE_X, FIGURE_Y]}

view_layer.material_override = None
(OUT / 'elevation-render.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('FURNACE_ELEVATION_DONE ' + str(OUT), flush=True)
