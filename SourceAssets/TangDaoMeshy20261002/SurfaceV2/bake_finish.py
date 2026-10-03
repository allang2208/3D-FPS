"""Bake fine surface relief over the complete original structural normal map."""
import bpy
import numpy as np
from pathlib import Path

P = Path(__file__).resolve().parent
S = P.parent
bpy.ops.wm.open_mainfile(filepath=str(S / 'TangDao_Modular_Editable.blend'))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 4
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
material = bpy.data.materials['M_TangDaoSurface']
nt = material.node_tree
nt.nodes.clear()

def node(kind):
    return nt.nodes.new(kind)

def math_node(op, a, b=None):
    n = node('ShaderNodeMath')
    n.operation = op
    for value, socket in [(a, n.inputs[0]), (b, n.inputs[1])]:
        if value is None:
            continue
        if isinstance(value, (float, int)):
            socket.default_value = value
        else:
            nt.links.new(value, socket)
    return n.outputs[0]

def texture(name, srgb=False, original=False):
    n = node('ShaderNodeTexImage')
    n.image = bpy.data.images.load(str((S / 'Textures' if original else P / 'Textures') / name), check_existing=True)
    n.image.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
    return n

bs = node('ShaderNodeBsdfPrincipled')
out = node('ShaderNodeOutputMaterial')
nt.links.new(bs.outputs[0], out.inputs['Surface'])
base = texture('TangDao_BaseColor.png', True)
orm = texture('TangDao_ORM.png')
channels = node('ShaderNodeSeparateColor')
nt.links.new(orm.outputs['Color'], channels.inputs[0])
nt.links.new(base.outputs['Color'], bs.inputs['Base Color'])
nt.links.new(channels.outputs['Green'], bs.inputs['Roughness'])
nt.links.new(channels.outputs['Blue'], bs.inputs['Metallic'])
struct = texture('Image_2.png', original=True)
normal = node('ShaderNodeNormalMap')
nt.links.new(struct.outputs['Color'], normal.inputs['Color'])
regions = texture('TangDao_Regions.png')
region = node('ShaderNodeSeparateColor')
nt.links.new(regions.outputs['Color'], region.inputs[0])
geometry = node('ShaderNodeNewGeometry')
xyz = node('ShaderNodeSeparateXYZ')
nt.links.new(geometry.outputs['Position'], xyz.inputs[0])
x, y, z = [xyz.outputs[k] for k in ['X', 'Y', 'Z']]
u = math_node('MULTIPLY', math_node('ARCTAN2', y, math_node('ADD', x, .014)), .015)
a = math_node('MULTIPLY', math_node('ADD', math_node('MULTIPLY', u, .82), math_node('MULTIPLY', z, .57)), 2 * np.pi / .0012)
b = math_node('MULTIPLY', math_node('ADD', math_node('MULTIPLY', u, -.57), math_node('MULTIPLY', z, .82)), 2 * np.pi / .0012)
weave = math_node('MULTIPLY', math_node('SINE', a), math_node('SINE', b))
weave = math_node('MULTIPLY', math_node('MULTIPLY', weave, region.outputs['Blue']), .000012)
grind = math_node('SINE', math_node('MULTIPLY', x, 2 * np.pi / .00045))
grind = math_node('MULTIPLY', math_node('MULTIPLY', grind, region.outputs['Red']), .0000004)
height = math_node('ADD', weave, grind)
bump = node('ShaderNodeBump')
bump.inputs['Strength'].default_value = 1
bump.inputs['Distance'].default_value = 1
nt.links.new(height, bump.inputs['Height'])
nt.links.new(normal.outputs['Normal'], bump.inputs['Normal'])
nt.links.new(bump.outputs['Normal'], bs.inputs['Normal'])
obj = bpy.data.objects['SM_TangDao']
for other in scene.objects:
    if other.type == 'MESH':
        other.hide_render = other != obj
        other.hide_set(other != obj)
bpy.ops.object.select_all(action='DESELECT')
obj.hide_set(False)
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
image = bpy.data.images.new('TangDao finished tangent normal', width=4096, height=4096, alpha=False)
image.colorspace_settings.name = 'Non-Color'
target = node('ShaderNodeTexImage')
target.image = image
nt.nodes.active = target
scene.render.bake.normal_space = 'TANGENT'
scene.render.bake.margin = 12
bpy.ops.object.bake(type='NORMAL')
image.filepath_raw = str(P / 'Textures/TangDao_Normal.png')
image.file_format = 'PNG'
image.save()
# Production source uses the finished atlas just as the UE material does.
nt.links.remove(bs.inputs['Normal'].links[0])
finished = node('ShaderNodeNormalMap')
nt.links.new(target.outputs['Color'], finished.inputs['Color'])
nt.links.new(finished.outputs['Normal'], bs.inputs['Normal'])
for n in list(nt.nodes):
    if n not in [bs, out, base, orm, channels, target, finished]:
        nt.nodes.remove(n)
for obj in scene.objects:
    if obj.type == 'MESH':
        obj.hide_render = False
        obj.hide_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'TangDao_SurfaceV2_Editable.blend'))
print('TANGDAO_FINISHED_NORMAL_AND_SOURCE_SAVED', flush=True)
