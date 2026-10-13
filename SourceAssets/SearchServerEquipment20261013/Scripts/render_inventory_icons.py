"""Author transparent inventory textures from the authored models."""
from pathlib import Path
from mathutils import Vector, Matrix
import bpy
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
sys.path.insert(0,str(PROJECT/'Tools/AssetPipeline'))
from collection_icon_orientation import orient_collection_camera
OUT = PROJECT / 'Content/ColdSteelData/Icons/SearchServerEquipment20261013'
OUT.mkdir(parents=True, exist_ok=True)
SPEC = json.loads((ROOT / 'model_manifest.json').read_text('utf-8'))
DIRECTIONS = dict(RAM=(0,-8,13), NIC=(-3,-9,13), HDD=(2,-9,13), SSD=(2,-9,13), CPU=(5,-8,12), GPU=(-2,-9,13), RAID=(-4,-8,13), Compute=(-2,-9,11))
GRIDS = {key:(spec['grid_w'],spec['grid_h']) for key,spec in SPEC['assets'].items()}
report = dict(stage='rendering', source='Authored GLB models',
              renderer='Blender Cycles', transparent=True, icons=[])

def point_at(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()

def bounds(objects):
    points = [o.matrix_world @ Vector(corner) for o in objects for corner in o.bound_box]
    low = Vector([min(p[i] for p in points) for i in range(3)])
    high = Vector([max(p[i] for p in points) for i in range(3)])
    return low, high, points

for key, spec in SPEC['assets'].items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=spec['glb'])
    objects = [o for o in scene.objects if o.type == 'MESH']
    transforms = [(o, o.matrix_world.copy()) for o in objects]
    for obj, transform in transforms:
        obj.parent = None
        obj.matrix_world = transform
    low, high, _ = bounds(objects)
    scale = Matrix.Scale(2.8/max(high-low), 4)
    for obj in objects: obj.matrix_world = scale @ obj.matrix_world
    bpy.context.view_layer.update()
    low, high, _ = bounds(objects)
    offset = -(low+high)*.5
    for obj in objects: obj.matrix_world.translation += offset
    bpy.context.view_layer.update()
    low, high, points = bounds(objects)

    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 128
    scene.cycles.use_denoising = True
    scene.cycles.adaptive_threshold = .012
    scene.cycles.max_bounces = 7
    scene.cycles.device = 'CPU'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'OPTIX'
        prefs.get_devices()
        if any(d.type == 'OPTIX' for d in prefs.devices):
            for d in prefs.devices: d.use = d.type == 'OPTIX'
            scene.cycles.device = 'GPU'
    except Exception as error:
        print('ICON_CPU_FALLBACK', str(error), flush=True)
    grid_w,grid_h=GRIDS[key]
    scene.render.resolution_x = 512 if grid_w==grid_h else 256*grid_w
    scene.render.resolution_y = 512 if grid_w==grid_h else 256*grid_h
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = 0
    scene.world = bpy.data.worlds.new('Inventory soft studio')
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (.55, .57, .60, 1)
    background.inputs['Strength'].default_value = .38
    for name, location, power, size in (
        ('Key', (-3.5, -4, 6), 650, 4),
        ('Fill', (4, -1.5, 3.8), 420, 3.5),
        ('Rim', (1, 4.5, 5), 850, 3)):
        light = bpy.data.lights.new(name, 'AREA')
        light.energy = power
        light.shape = 'DISK'
        light.size = size
        obj = bpy.data.objects.new(name, light)
        scene.collection.objects.link(obj)
        obj.location = location
        point_at(obj, (0, 0, 0))
    camera = bpy.data.cameras.new('Inventory orthographic camera')
    camera.type = 'ORTHO'
    obj = bpy.data.objects.new(camera.name, camera)
    scene.collection.objects.link(obj)
    obj.location = Vector(DIRECTIONS[key]).normalized()*10
    point_at(obj, (0, 0, 0))
    orientation=orient_collection_camera(obj,*GRIDS[key],dimensions=spec.get('actual_dimensions_cm',spec.get('dimensions')))
    scene.camera = obj
    bpy.context.view_layer.update()
    inverse = obj.matrix_world.inverted()
    frame = [inverse @ p for p in points]
    width = max(p.x for p in frame)-min(p.x for p in frame)
    height = max(p.y for p in frame)-min(p.y for p in frame)
    aspect=scene.render.resolution_x/scene.render.resolution_y
    fit_width=max(width,height*aspect)*1.10
    camera.ortho_scale=fit_width if aspect>=1 else fit_width/aspect
    file = OUT / (spec['id']+'.png')
    scene.render.filepath = str(file)
    bpy.ops.render.render(write_still=True)
    report['icons'].append(dict(id=spec['id'], name=spec['name'], file=str(file),
        ue_icon=str(file.relative_to(PROJECT/'Content/ColdSteelData')).replace('\\', '/'),
        grid_w=GRIDS[key][0], grid_h=GRIDS[key][1], pixel_size=[scene.render.resolution_x,scene.render.resolution_y], source=spec['glb'],orientation=orientation))
    print('INVENTORY_ICON_SAVED', spec['id'], GRIDS[key], flush=True)
    (ROOT/'inventory_icons.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report['stage'] = 'icons_saved'
(ROOT/'inventory_icons.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SERVER_INVENTORY_ICONS_COMPLETE', len(report['icons']), flush=True)
