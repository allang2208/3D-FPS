"""Give the M4 and QBZ-191 extended magazines the accepted per-rifle finish.

This reuses the two accepted finish routes instead of inventing another one:

* M4A1  - WeaponAttachmentFinish20260913/author_uv.py: a physical-projection UV
          (tile 12x5 cm, one channel per face by dominant normal axis) added
          without touching UV0 or the split normals. That UV is what the already
          installed M4 attachment finish materials sample, so the magazine can
          take that same material.
* QBZ-191 - QBZ191MetalCoat20260913/bake_coating.py: the rifle's authored
          receiver coating (plus its contact wear) baked onto the part's own
          coating atlas, which is what every accepted QBZ attachment uses.

Run: blender -b -P author_extmag_finish.py
"""
import ast
import bpy
import json
import math
import os
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
S = ROOT.parent                                   # SourceAssets
FBXDIR = ROOT / 'FBX'
TEXDIR = ROOT / 'Textures'
M4_TILE = (0.12, 0.05)
QBZ_SIZE = 2048


def import_fbx(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=str(path))
    return [o for o in bpy.context.scene.objects if o not in before and o.type == 'MESH']


def export(ob, path):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    for other in [o for o in bpy.context.scene.objects if o is not ob]:
        bpy.data.objects.remove(other, do_unlink=True)
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'MESH'},
                             axis_forward='-Y', axis_up='Z', bake_anim=False,
                             mesh_smooth_type='FACE', use_tspace=True)


report = {}

# ---------------------------------------------------------------- M4: physical UV
bpy.ops.wm.read_factory_settings(use_empty=True)
ob = import_fbx(FBXDIR / 'SM_ExtMag_M440_factory.fbx')[-1]
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
mesh = ob.data
while len(mesh.uv_layers) > 1:                     # drop the rejected bake UV
    mesh.uv_layers.remove(mesh.uv_layers[-1])
uv_index = len(mesh.uv_layers)
uv = mesh.uv_layers.new(name='ReceiverFinishPhysicalUV')
for face in mesh.polygons:
    axis = max(range(3), key=lambda i: abs(face.normal[i]))
    axes = ([1, 2] if axis == 0 else [0, 2] if axis == 1 else [0, 1])
    for loop_index in face.loop_indices:
        vertex = mesh.vertices[mesh.loops[loop_index].vertex_index].co
        uv.data[loop_index].uv = (vertex[axes[0]] / M4_TILE[0] + .5,
                                  vertex[axes[1]] / M4_TILE[1] + .5)
mesh.uv_layers.active_index = 0
mesh.uv_layers[0].active_render = True
m4_out = FBXDIR / 'SM_ExtMag_M440_finish_uv.fbx'
export(ob, m4_out)
report['M4'] = {'file': str(m4_out), 'uv_index': uv_index, 'physical_tile_m': list(M4_TILE),
                'uv_layers': [layer.name for layer in mesh.uv_layers],
                'note': 'author_uv.py rule: keep UV0/split normals, add physical UV'}
print('EXTMAG_FINISH_M4_UV', uv_index, flush=True)

# ------------------------------------------------------------- QBZ: receiver coating
bpy.ops.wm.read_factory_settings(use_empty=True)
source = ast.parse((S / 'QBZ191Hero20260913' / 'build.py').read_text())
function = next(x for x in source.body if isinstance(x, ast.FunctionDef) and x.name == 'material')
exec(compile(ast.Module(body=[function], type_ignores=[]), 'receiver_material_source', 'exec'))
coating = material('AUTH_QBZ191_ReceiverCoating', (.025, .029, .033), .72, .30)
coating.use_fake_user = True
nodes = coating.node_tree.nodes
links = coating.node_tree.links
bsdf = next(x for x in nodes if x.type == 'BSDF_PRINCIPLED')
output = next(x for x in nodes if x.type == 'OUTPUT_MATERIAL')
for tex in list(nodes):
    if tex.type == 'TEX_IMAGE' and tex.label == 'Original colour and markings reference':
        for link in list(tex.outputs['Color'].links):
            if link.to_node.type == 'MIX_RGB':
                link.to_node.inputs[0].default_value = 0.
metal_node = nodes.new('ShaderNodeValue')
metal_node.outputs[0].default_value = .72
n = nodes                      # the wear recipe uses bake_coating.py's short names
l = links
bs = bsdf
base = bs.inputs['Base Color'].links[0].from_socket
rough = bs.inputs['Roughness'].links[0].from_socket
normal = bs.inputs['Normal'].links[0].from_socket
metal = metal_node.outputs[0]
group = 'Body'
wear = (S / 'QBZ191ContactWear20260913' / 'wear.py').read_text()
exec(textwrap.dedent(wear[wear.index(' def mathnode'):wear.index(' emit=n.new')]))
base = bsdf.inputs['Base Color'].links[0].from_socket
rough = bsdf.inputs['Roughness'].links[0].from_socket
metal = bsdf.inputs['Metallic'].links[0].from_socket


def mathnode(operation, a, b):
    node = nodes.new('ShaderNodeMath')
    node.operation = operation
    for index, value in enumerate([a, b]):
        if isinstance(value, (int, float)):
            node.inputs[index].default_value = value
        else:
            links.new(value, node.inputs[index])
    return node.outputs[0]


blend = nodes.new('ShaderNodeMixRGB')
blend.inputs[0].default_value = .32
blend.inputs[2].default_value = (.025, .029, .032, 1)
links.new(base, blend.inputs[1])
base = blend.outputs[0]
rough = mathnode('ADD', mathnode('MULTIPLY', rough, .62), .42 * .38)
links.new(base, bsdf.inputs['Base Color'])
links.new(rough, bsdf.inputs['Roughness'])
orm = nodes.new('ShaderNodeCombineColor')
orm.inputs[0].default_value = 1
links.new(rough, orm.inputs[1])
links.new(metal, orm.inputs[2])
emit = nodes.new('ShaderNodeEmission')
target = nodes.new('ShaderNodeTexImage')
nodes.active = target

qbz = import_fbx(FBXDIR / 'SM_ExtMag_QBZ40_factory.fbx')[-1]
bpy.ops.object.select_all(action='DESELECT')
qbz.select_set(True)
bpy.context.view_layer.objects.active = qbz
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
mesh = qbz.data
while len(mesh.uv_layers) > 1:
    mesh.uv_layers.remove(mesh.uv_layers[-1])
coat_index = len(mesh.uv_layers)
coat = mesh.uv_layers.new(name='QBZCoatingUV')
mesh.uv_layers.active_index = coat_index
coat.active_render = True
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.012,
                         area_weight=.2, correct_aspect=True, scale_to_bounds=True)
bpy.ops.object.mode_set(mode='OBJECT')

original_materials = list(mesh.materials)
original_indices = [face.material_index for face in mesh.polygons]
for index in range(len(mesh.materials)):
    mesh.materials[index] = coating
maps = {}
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 8
scene.render.bake.use_selected_to_active = False
scene.render.bake.use_clear = True
scene.render.bake.margin = 12
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'OPTIX'
prefs.get_devices()
for device in prefs.devices:
    device.use = device.type == 'OPTIX'
if any(device.use for device in prefs.devices):
    scene.cycles.device = 'GPU'

out_dir = TEXDIR / 'QBZ'
out_dir.mkdir(parents=True, exist_ok=True)
for kind, socket in (('BaseColor', base), ('ORM', orm.outputs[0])):
    image = bpy.data.images.new('T_ExtMag_QBZ191_%s' % kind, width=QBZ_SIZE, height=QBZ_SIZE, alpha=False)
    image.colorspace_settings.name = 'sRGB' if kind == 'BaseColor' else 'Non-Color'
    target.image = image
    links.new(socket, emit.inputs['Color'])
    links.new(emit.outputs[0], output.inputs['Surface'])
    qbz.hide_render = False
    bpy.ops.object.bake(type='EMIT')
    image.filepath_raw = str(out_dir / (image.name + '.png'))
    image.file_format = 'PNG'
    image.save()
    maps[kind] = image.filepath_raw
    print('EXTMAG_FINISH_QBZ_BAKED', kind, flush=True)

for index, material_ in enumerate(original_materials):
    mesh.materials[index] = material_
for face, index in zip(mesh.polygons, original_indices):
    face.material_index = index
mesh.uv_layers.active_index = 0
mesh.uv_layers[0].active_render = True
qbz_out = FBXDIR / 'SM_ExtMag_QBZ40_finish_uv.fbx'
export(qbz, qbz_out)
report['QBZ'] = {'file': str(qbz_out), 'uv_index': coat_index, 'textures': maps,
                 'uv_layers': [layer.name for layer in mesh.uv_layers],
                 'note': 'bake_coating.py rule: rifle coating + contact wear on the part atlas'}
print('EXTMAG_FINISH_QBZ_UV', coat_index, flush=True)

(ROOT / 'Reference' / 'finish_authoring.json').write_text(
    json.dumps(report, indent=1, ensure_ascii=False))
print('EXTMAG_FINISH_AUTHORED ' + json.dumps(report, ensure_ascii=False), flush=True)
