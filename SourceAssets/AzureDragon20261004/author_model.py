"""Adapt the user's downloaded Fab Dragon Claw without changing its silhouette."""
import bpy
import json
from pathlib import Path
from mathutils import Vector
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'Export'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT / 'Original/Fisto.glb'))
objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
if not objects:
    raise RuntimeError('Downloaded Dragon Claw contains no mesh')
for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = objects[0]
bpy.ops.object.join()
obj = bpy.context.object
obj.name = 'SM_AzureDragonClaw'
# glTF source +Z points to the metal nails. Blender imports that as -Y.
# Put forward on +X and retain up on +Z; UE receives centimetre vertices.
points = [Vector((-p.y, p.x, p.z)) for p in (obj.matrix_world @ v.co for v in obj.data.vertices)]
lo = Vector(tuple(min(p[i] for p in points) for i in range(3)))
hi = Vector(tuple(max(p[i] for p in points) for i in range(3)))
scale = 125.0 / (hi.x - lo.x)
center = Vector((lo.x + (hi.x-lo.x)*.36, (lo.y+hi.y)*.5, (lo.z+hi.z)*.5))
for v, p in zip(obj.data.vertices, points):
    v.co = (p-center)*scale
obj.matrix_world.identity()

# Combine the author's original normal maps in UV tiles. All three surface
# regions can share one energy material while preserving scales and leather grain.
atlas = np.empty((2048, 2048, 4), dtype=np.float32)
atlas[:] = [.5, .5, 1., 1.]
normal_images = {image.name: image for image in bpy.data.images}
materials = list(obj.data.materials)
tiles = [(0,0), (1,0), (0,1)]
for slot, material in enumerate(materials):
    image = None
    if material and material.use_nodes:
        for n in material.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image and 'normal' in n.image.name.lower():
                image = n.image; break
    tx, ty = tiles[min(slot, 2)]
    if image:
        image.scale(1024, 1024)
        pixels = np.empty(1024*1024*4, dtype=np.float32)
        image.pixels.foreach_get(pixels)
        pixels = pixels.reshape((1024,1024,4))
        pixels[:,:,1] = 1.0-pixels[:,:,1]  # glTF OpenGL -> UE DirectX tangent normal
        atlas[ty*1024:(ty+1)*1024, tx*1024:(tx+1)*1024] = pixels
uv = obj.data.uv_layers.active
if not uv:
    raise RuntimeError('Dragon Claw requires its original UVs')
for polygon in obj.data.polygons:
    tx, ty = tiles[min(polygon.material_index, 2)]
    for loop in polygon.loop_indices:
        original = uv.data[loop].uv.copy()
        uv.data[loop].uv = ((original.x+tx)*.5, (original.y+ty)*.5)
    polygon.material_index = 0
obj.data.materials.clear()
obj.data.materials.append(bpy.data.materials.new('AzureDragonEnergy'))
image = bpy.data.images.new('T_AzureDragonNormal', width=2048, height=2048, alpha=False)
image.colorspace_settings.name = 'Non-Color'
image.pixels.foreach_set(atlas.ravel())
image.filepath_raw = str(OUT / 'T_AzureDragonNormal.png')
image.file_format = 'PNG'
image.save()
image.pack()
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = .01
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
for source_image in bpy.data.images:
    if source_image.has_data:
        source_image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'AzureDragonClaw.blend'))
manifest = {'source': 'Original/Fisto.glb', 'author': 'CaptainHC',
            'source_listing': 'https://www.fab.com/listings/2d436c6f-7d26-4a80-8469-884b97613e5a',
            'adaptation_blend': str(ROOT / 'AzureDragonClaw.blend'),
            'normal': str(OUT / 'T_AzureDragonNormal.png'),
            'length_cm': 125, 'forward': '+X', 'up': '+Z',
            'triangles': sum(len(p.vertices)-2 for p in obj.data.polygons),
            'rigged': False, 'shape_retained': True, 'runtime_tested': False, 'rendered': False}
(OUT / 'model.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('AZURE_DRAGON_GEOMETRY_EXPORTED')
