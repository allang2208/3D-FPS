"""Render the requested new Meshy candidate; never modify or export its mesh."""
import bpy
import json
from mathutils import Vector
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'Meshy/lmg201_new_reference_smooth_v01/downloads/model_urls_glb.glb'
OUT = ROOT / 'Preview'
OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
points = [o.matrix_world @ Vector(v) for o in meshes for v in o.bound_box]
lo = Vector([min(p[i] for p in points) for i in range(3)])
hi = Vector([max(p[i] for p in points) for i in range(3)])
center = (lo + hi) / 2
size = hi - lo
scale = 2.0 / max(size)
root = bpy.data.objects.new('Preview framing only', None)
bpy.context.collection.objects.link(root)
for ob in list(bpy.context.scene.objects):
    if ob != root and ob.parent is None:
        ob.parent = root
root.scale = (scale,) * 3
root.location = -center * scale
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.cycles.device = 'CPU'
scene.render.resolution_x = 1800
scene.render.resolution_y = 850
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX'
world = bpy.data.worlds.new('Neutral studio')
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.065, 0.075, 0.09, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.5

def aim(ob, target):
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat('-Z', 'Y').to_euler()

def area(name, location, power, size):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = power
    data.shape = 'DISK'
    data.size = size
    ob = bpy.data.objects.new(name, data)
    scene.collection.objects.link(ob)
    ob.location = location
    aim(ob, (0, 0, 0))

area('Broad key', (-0.8, -1.4, 2.0), 220, 2)
area('Fill', (0.8, -1.1, 0.3), 80, 1.5)
area('Edge', (0.1, 1.5, 1.1), 160, 1.5)
cam_data = bpy.data.cameras.new('Candidate camera')
cam = bpy.data.objects.new('Candidate camera', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.type = 'ORTHO'
cam_data.lens = 50
cam_data.clip_start = 0.01
cam_data.clip_end = 100

# Imported glTF uses Blender Z-up; determine its longitudinal horizontal axis.
long_x = size.x >= size.y
def pose(close=False):
    cam.location = (0.05, -3, 0.8) if long_x else (3, 0.05, 0.8)
    aim(cam, (0, 0, 0.015 if close else 0))
    cam_data.ortho_scale = 1.15 if close else 2.18
    scene.render.resolution_x = 1600 if close else 1800
    scene.render.resolution_y = 1000 if close else 850

def render(name, close=False):
    pose(close)
    scene.render.filepath = str(OUT / name)
    bpy.ops.render.render(write_still=True)

render('candidate_pbr.png')
render('receiver_pbr.png', True)
clay = bpy.data.materials.new('Neutral clay - render only')
clay.use_nodes = True
bsdf = clay.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = (0.27, 0.29, 0.32, 1)
bsdf.inputs['Roughness'].default_value = 0.42
bsdf.inputs['Metallic'].default_value = 0
for ob in meshes:
    for slot in ob.material_slots:
        slot.material = clay
render('receiver_geometry.png', True)
report = {
    'source': str(SOURCE),
    'source_geometry_modified': False,
    'source_materials_modified': False,
    'mesh_objects': len(meshes),
    'vertices': sum(len(o.data.vertices) for o in meshes),
    'triangles': sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes),
    'imported_bounds': {'min': list(lo), 'max': list(hi)},
    'purpose': 'Requested candidate appearance comparison, not UE runtime acceptance',
    'clay_note': 'Same imported geometry and normals, no textures or normal maps; no smoothing, subdivision or remeshing applied.'
}
(OUT / 'preview_manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('CANDIDATE_PREVIEWS_SAVED', flush=True)
