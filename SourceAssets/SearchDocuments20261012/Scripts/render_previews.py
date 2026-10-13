"""User-requested previews of the delivered GLB meshes. No source asset edits."""
from pathlib import Path
import bpy
import json
import math
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Previews'
OUT.mkdir(exist_ok=True)
SPEC = json.loads((ROOT / 'model_manifest.json').read_text('utf-8'))
report = dict(source='Delivered GLB geometry and embedded PBR textures',
              renderer='Blender Cycles', game_capture=False, previews=[])

def point_at(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()

def bounds(objects):
    points = [o.matrix_world @ Vector(corner) for o in objects for corner in o.bound_box]
    low = Vector([min(p[i] for p in points) for i in range(3)])
    high = Vector([max(p[i] for p in points) for i in range(3)])
    return low, high, points

def studio(scene):
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.cycles.adaptive_threshold = .02
    scene.cycles.max_bounces = 7
    scene.cycles.transparent_max_bounces = 4
    scene.cycles.device = 'CPU'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'OPTIX'
        prefs.get_devices()
        available = [d for d in prefs.devices if d.type == 'OPTIX']
        if available:
            for d in prefs.devices: d.use = d.type == 'OPTIX'
            scene.cycles.device = 'GPU'
            print('PREVIEW_GPU', [d.name for d in available], flush=True)
    except Exception as error:
        print('PREVIEW_CPU_FALLBACK', str(error), flush=True)
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = 0
    scene.world = bpy.data.worlds.new('Preview neutral studio')
    scene.world.use_nodes = True
    world = scene.world.node_tree.nodes.get('Background')
    world.inputs['Color'].default_value = (.55, .57, .60, 1)
    world.inputs['Strength'].default_value = .32
    for name, position, energy, size in (
        ('Key softbox', (-3.5, -4, 6), 650, 4),
        ('Fill softbox', (4, -1.5, 3.8), 370, 3.5),
        ('Rear softbox', (1, 4.5, 5), 850, 3)):
        light = bpy.data.lights.new(name, 'AREA')
        light.energy = energy
        light.shape = 'DISK'
        light.size = size
        obj = bpy.data.objects.new(name, light)
        scene.collection.objects.link(obj)
        obj.location = position
        point_at(obj, (0, 0, .2))
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.012))
    floor = bpy.context.object
    floor.name = 'Preview backdrop only'
    material = bpy.data.materials.new('Preview warm gray floor')
    material.use_nodes = True
    surface = material.node_tree.nodes.get('Principled BSDF')
    surface.inputs['Base Color'].default_value = (.165, .173, .18, 1)
    surface.inputs['Roughness'].default_value = .86
    floor.data.materials.append(material)
    camera = bpy.data.cameras.new('Preview camera')
    camera.type = 'ORTHO'
    camera.lens = 70
    obj = bpy.data.objects.new('Preview camera', camera)
    scene.collection.objects.link(obj)
    scene.camera = obj
    return obj

directions = dict(USB=(-6, -8, 7), Tape=(6, -8, 8),
                  Case=(6, -8, 6.8), Archive=(5, -8, 10))
details = dict(USB=(-8, -3, 4.2), Tape=(5, -7, 7),
               Case=(-3.5, -9, 3.5), Archive=(-6, -8, 4.3))

for key, spec in SPEC['assets'].items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=spec['glb'])
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    transforms = [(o, o.matrix_world.copy()) for o in objects]
    for o, transform in transforms:
        o.parent = None
        o.matrix_world = transform
    low, high, _ = bounds(objects)
    size = max(high-low)
    scale = Matrix.Scale(2.8/size, 4)
    for o in objects: o.matrix_world = scale @ o.matrix_world
    bpy.context.view_layer.update()
    low, high, _ = bounds(objects)
    offset = Vector((-(low.x+high.x)*.5, -(low.y+high.y)*.5, -low.z))
    for o in objects: o.matrix_world.translation += offset
    bpy.context.view_layer.update()
    scene = bpy.context.scene
    camera = studio(scene)
    for angle in ('hero', 'detail'):
        if key == 'Tape' and angle == 'detail':
            for o in objects: o.matrix_world = Matrix.Rotation(math.pi, 4, 'X') @ o.matrix_world
            bpy.context.view_layer.update()
            low, high, _ = bounds(objects)
            for o in objects: o.matrix_world.translation.z -= low.z
            bpy.context.view_layer.update()
        low, high, points = bounds(objects)
        centre = (low+high)*.5
        direction = Vector((directions if angle == 'hero' else details)[key]).normalized()
        camera.location = centre + direction*10
        point_at(camera, centre)
        bpy.context.view_layer.update()
        inverse = camera.matrix_world.inverted()
        projected = [inverse @ p for p in points]
        width = max(p.x for p in projected)-min(p.x for p in projected)
        height = max(p.y for p in projected)-min(p.y for p in projected)
        camera.data.ortho_scale = max(height, width/(1600/1200))*1.34
        # Blender ortho_scale describes horizontal camera width in landscape mode.
        camera.data.ortho_scale *= 1600/1200
        filepath = OUT / (key+'_'+angle+'.png')
        scene.render.filepath = str(filepath)
        print('RENDER_START', key, angle, flush=True)
        bpy.ops.render.render(write_still=True)
        report['previews'].append(dict(item_id=spec['id'], key=key, angle=angle,
            file=str(filepath), source=spec['glb'],
            note='Underside view' if key == 'Tape' and angle == 'detail' else 'Exterior view'))
        (OUT / 'preview_manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print('RENDER_SAVED', filepath, flush=True)
print('PREVIEWS_COMPLETE', len(report['previews']), flush=True)
delivery_path = ROOT / 'delivery.json'
delivery = json.loads(delivery_path.read_text('utf-8'))
delivery.update(rendered=True, preview_manifest='Previews/preview_manifest.json',
                preview_renderer='Blender Cycles using delivered GLB',
                preview_count=len(report['previews']), game_capture=False)
delivery_path.write_text(json.dumps(delivery, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
