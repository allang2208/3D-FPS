"""Bake authoring coordinates from the actual fitted knife into its existing UV0."""
import bpy
import numpy as np
from pathlib import Path

P = Path(__file__).resolve().parent
S = P.parent
P.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(S / 'TangDao_Modular_Editable.blend'))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 1
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    devices = [d for d in prefs.devices if d.type == 'OPTIX']
    for d in prefs.devices:
        d.use = d in devices
    if devices:
        scene.cycles.device = 'GPU'
except Exception:
    pass
obj = bpy.data.objects['SM_TangDao']
for other in scene.objects:
    if other.type == 'MESH':
        other.hide_render = other != obj
        other.hide_set(other != obj)
bpy.ops.object.select_all(action='DESELECT')
obj.hide_set(False)
obj.hide_render = False
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
material = bpy.data.materials.new('TangDao SurfaceV2 coordinate authoring')
material.use_nodes = True
obj.data.materials.clear()
obj.data.materials.append(material)
nt = material.node_tree
nt.nodes.clear()
geometry = nt.nodes.new('ShaderNodeNewGeometry')
emission = nt.nodes.new('ShaderNodeEmission')
output = nt.nodes.new('ShaderNodeOutputMaterial')
nt.links.new(emission.outputs[0], output.inputs['Surface'])
target = nt.nodes.new('ShaderNodeTexImage')
packed = {}
for key, socket in [('position', 'Position'), ('normal', 'Normal')]:
    image = bpy.data.images.new('TangDao_' + key, width=4096, height=4096, alpha=True, float_buffer=True)
    image.generated_color = (0, 0, 0, 0)
    image.colorspace_settings.name = 'Non-Color'
    target.image = image
    nt.nodes.active = target
    vector = nt.nodes.new('ShaderNodeVectorMath')
    vector.operation = 'MULTIPLY_ADD'
    vector.inputs[1].default_value = (1 / .4, 1 / .3, 1 / 1.2) if key == 'position' else (.5, .5, .5)
    vector.inputs[2].default_value = (.5, .5, .25) if key == 'position' else (.5, .5, .5)
    nt.links.new(geometry.outputs[socket], vector.inputs[0])
    nt.links.new(vector.outputs[0], emission.inputs['Color'])
    scene.render.bake.margin = 12
    bpy.ops.object.bake(type='EMIT')
    pixels = np.empty(4096 * 4096 * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    packed[key] = np.flipud(pixels.reshape(4096, 4096, 4)).astype(np.float16)
    nt.nodes.remove(vector)
    print('TANGDAO_COORDINATE_BAKED ' + key, flush=True)
np.savez_compressed(P / 'surface_coordinates.npz', **packed)
print('TANGDAO_COORDINATES_SAVED', flush=True)
