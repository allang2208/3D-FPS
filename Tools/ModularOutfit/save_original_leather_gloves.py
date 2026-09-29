"""Create the editable V7 glove master, real pickup mesh and requested inventory icon.

Run with Blender in background. This produces artwork, not gameplay previews.
Native UE variants are derived from the existing fitted native meshes by the importer.
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector, Euler

sys.path.insert(0, str(Path(__file__).resolve().parent))
from original_leather_gloves import PROJECT as P, ROOT as R, read, write
from glove_icon_display import posed_surface

# Keep this established production entry on the user's selected leather style.
# V1 remains a source for the full-finger icon geometry, never its new material.
if (R.parent/'OriginalLeatherV2/published.json').exists():
    import runpy
    import subprocess
    subprocess.run(['C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe',
                    str(P/'Tools/ModularOutfit/prepare_original_tailored_leather.py')], check=True)
    runpy.run_path(str(P/'Tools/ModularOutfit/bake_original_tailored_leather.py'), run_name='__main__')
    raise SystemExit(0)

SOURCE = P/'SourceAssets/ModularOutfit20260925/FittedFieldGlovesV1/Authored/M4.json'
SCAN = P/'SourceAssets/HandEquipmentAppearance/Source'
FIELDS = P/'SourceAssets/ModularOutfit20260925/FieldGlovesLeatherV1'
data = read(SOURCE)
bones = read(P/'SourceAssets/ModularOutfit20260925/BareArmsFamilyV6/Sources/M4.json')['bones']
anatomy = read(P/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']
R.mkdir(parents=True, exist_ok=True)
write(R/'M4_OriginalLeatherV1.json', data)
bpy.ops.wm.read_factory_settings(use_empty=True)


def material():
    mat = bpy.data.materials.new('OriginalBrownLeather')
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bs = nodes.get('Principled BSDF')
    bs.inputs['Metallic'].default_value = 0
    bs.inputs['Specular IOR Level'].default_value = .32
    coord = nodes.new('ShaderNodeTexCoord')
    mapping = nodes.new('ShaderNodeVectorMath'); mapping.operation = 'SCALE'
    mapping.inputs['Scale'].default_value = 4.0  # 25 cm leather scan
    links.new(coord.outputs['Object'], mapping.inputs[0])

    def tex(path, color=False, tiled=False):
        t = nodes.new('ShaderNodeTexImage')
        t.image = bpy.data.images.load(str(path), check_existing=True)
        t.image.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
        if tiled:
            t.projection = 'BOX'; t.projection_blend = .25
            links.new(mapping.outputs['Vector'], t.inputs['Vector'])
        return t.outputs['Color']

    def mathnode(op, a, b):
        n = nodes.new('ShaderNodeMath'); n.operation = op
        for i, value in enumerate((a, b)):
            if isinstance(value, (float, int)): n.inputs[i].default_value = value
            else: links.new(value, n.inputs[i])
        return n.outputs[0]

    def mix(mode, factor, a, b):
        n = nodes.new('ShaderNodeMixRGB'); n.blend_type = mode
        for slot, value in zip(n.inputs, (factor, a, b)):
            if isinstance(value, (tuple, float, int)): slot.default_value = value
            else: links.new(value, slot)
        return n.outputs[0]

    def scan(channel, color=False):
        return tex(SCAN/f'Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_{channel}.jpg', color, True)

    regions = nodes.new('ShaderNodeSeparateColor')
    links.new(tex(FIELDS/'T_FieldGloves_LeatherRegions.png'), regions.inputs[0])
    palm, stitch = regions.outputs['Green'], regions.outputs['Blue']
    color = mix('MULTIPLY', .22, scan('BaseColor', True), scan('AO'))
    color = mix('MULTIPLY', .14, color, scan('Cavity'))
    color = mix('MULTIPLY', palm, color, (.90, .90, .90, 1))
    color = mix('MIX', mathnode('MULTIPLY', stitch, .32), color, (.105, .065, .032, 1))
    links.new(color, bs.inputs['Base Color'])
    rough = mathnode('ADD', mathnode('ADD', .46, mathnode('MULTIPLY', palm, .15)), mathnode('MULTIPLY', scan('Roughness'), .22))
    links.new(rough, bs.inputs['Roughness'])
    # The licensed scan is OpenGL. The atlas thread normal is DirectX.
    grain = nodes.new('ShaderNodeNormalMap'); grain.inputs['Strength'].default_value = .32
    links.new(scan('Normal'), grain.inputs['Color'])
    thread = nodes.new('ShaderNodeNormalMap'); thread.inputs['Strength'].default_value = .70
    sep = nodes.new('ShaderNodeSeparateColor'); comb = nodes.new('ShaderNodeCombineColor')
    links.new(tex(FIELDS/'T_FieldGloves_StitchNormal.png'), sep.inputs[0])
    links.new(sep.outputs['Red'], comb.inputs['Red'])
    links.new(mathnode('SUBTRACT', 1.0, sep.outputs['Green']), comb.inputs['Green'])
    links.new(sep.outputs['Blue'], comb.inputs['Blue']); links.new(comb.outputs[0], thread.inputs['Color'])
    blended = mix('MIX', mathnode('MULTIPLY', stitch, .65), grain.outputs['Normal'], thread.outputs['Normal'])
    links.new(blended, bs.inputs['Normal'])
    return mat


leather = material()
lining = bpy.data.materials.new('DarkLeatherLining'); lining.use_nodes = True
lining.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.018, .009, .004, 1)
lining.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .88


def mesh_object(name, positions, faces, uvrows):
    mesh = bpy.data.meshes.new(name); mesh.from_pydata(positions, [], faces); mesh.update()
    obj = bpy.data.objects.new(name, mesh); bpy.context.collection.objects.link(obj)
    mesh.materials.append(leather); mesh.materials.append(lining)
    uv = mesh.uv_layers.new(name='OriginalLeatherUV')
    for face, row in zip(mesh.polygons, uvrows):
        face.use_smooth = True
        for loop, (u, v) in zip(face.loop_indices, row): uv.data[loop].uv = (u, 1-v)
    return obj


# Editable native reference master: accepted V7 hand envelope and fixed cuff.
reflection = Matrix.Diagonal((1, -1, 1))
arm = bpy.data.armatures.new('M4_NativeReference'); rig = bpy.data.objects.new(arm.name, arm)
bpy.context.collection.objects.link(rig); bpy.context.view_layer.objects.active = rig; rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
names = {b['index']: n for n, b in bones.items()}
for name, bone in bones.items():
    eb = arm.edit_bones.new(name); axes = Matrix(bone['axes']).transposed()
    for col in range(3): axes.col[col] = axes.col[col].normalized()
    matrix = (reflection@axes@reflection).to_4x4()
    matrix.translation = reflection@Vector(bone['position'])*.01
    eb.matrix = matrix; eb.length = .025
for name, bone in bones.items():
    if bone['parent'] in names: arm.edit_bones[name].parent = arm.edit_bones[names[bone['parent']]]
bpy.ops.object.mode_set(mode='OBJECT')
master = mesh_object('M4_OriginalLeatherV1', [(x*.01, -y*.01, z*.01) for x,y,z in data['positions']], data['triangles'], data['uv'])
master.parent = rig; mod = master.modifiers.new('NativeBinding', 'ARMATURE'); mod.object = rig
for name in sorted({n for weights in data['weights'] for n in weights}): master.vertex_groups.new(name=name)
for vi, weights in enumerate(data['weights']):
    for name, weight in weights.items(): master.vertex_groups[name].add([vi], weight, 'REPLACE')
master['Contract'] = 'V7 fitted full glove; existing skin weights, cuff and animations; no sleeves'
bpy.ops.wm.save_as_mainfile(filepath=str(R/'M4_OriginalLeatherV1.blend'))
bpy.data.objects.remove(master, do_unlink=True); bpy.data.objects.remove(rig, do_unlink=True)

# One empty glove, relaxed by the actual finger bones, with a readable wrist opening.
posed, selected = posed_surface(data, bones, anatomy, 'r')
faces = np.asarray(data['triangles'])[selected]; used = np.unique(faces)
remap = {int(vi): index for index, vi in enumerate(used)}
rotation = np.array(Euler(np.radians((-10, 18, -6)), 'XYZ').to_matrix())
positions = ((posed[used]-np.array([0, 7.5, 0]))*.01)@rotation.T
obj = mesh_object('SM_OriginalLeatherGloves_Pickup', positions.tolist(), [[remap[int(v)] for v in f] for f in faces], [data['uv'][int(fi)] for fi in selected])
shell = obj.modifiers.new('EmptyWristLining', 'SOLIDIFY'); shell.thickness = .0007; shell.offset = -1
shell.material_offset = 1; shell.material_offset_rim = 1
bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active = obj
bpy.ops.export_scene.fbx(filepath=str(R/'SM_OriginalLeatherGloves_Pickup.fbx'), use_selection=True, object_types={'MESH'}, apply_unit_scale=True, bake_anim=False, use_mesh_modifiers=True, add_leaf_bones=False, path_mode='STRIP')

scene = bpy.context.scene; scene.render.engine = 'CYCLES'; scene.cycles.samples = 64; scene.cycles.device = 'CPU'
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'; scene.render.image_settings.color_mode = 'RGBA'
scene.render.resolution_x = 320; scene.render.resolution_y = 320; scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'Standard'; scene.view_settings.exposure = 0
scene.world = bpy.data.worlds.new('LeatherStudio'); scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.25, .28, .34, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .12
for name, pos, power, size in [('Key',(-.7,-.8,1.6),90,.55), ('Fill',(1.1,.3,1.2),22,1.2), ('Rim',(.1,1,.9),40,.7)]:
    light = bpy.data.lights.new(name,'AREA'); light.energy = power; light.shape = 'DISK'; light.size = size
    lo = bpy.data.objects.new(name,light); scene.collection.objects.link(lo); lo.location = pos
    lo.rotation_euler = (-Vector(pos)).to_track_quat('-Z','Y').to_euler()
camera = bpy.data.cameras.new('InventoryCamera'); camera.type = 'ORTHO'; camera.clip_start = .01
cam = bpy.data.objects.new(camera.name,camera); scene.collection.objects.link(cam); scene.camera = cam
low = positions.min(0); high = positions.max(0)
camera.ortho_scale = float(max(high[:2]-low[:2])/.91)
cam.location = (float((low[0]+high[0])*.5),float((low[1]+high[1])*.5),1.5)
cam.rotation_euler = (0,0,0)
scene.render.filepath = str(R/'ue_original_gloves.png')
bpy.ops.wm.save_as_mainfile(filepath=str(R/'OriginalLeather_Icon.blend'))
bpy.ops.render.render(write_still=True)
write(R/'artwork.json', dict(master=str(R/'M4_OriginalLeatherV1.blend'), icon=str(R/'ue_original_gloves.png'), pickup=str(R/'SM_OriginalLeatherGloves_Pickup.fbx'), source=str(SOURCE), new_animations=0, runtime_tested=False))
print('ORIGINAL_LEATHER_ARTWORK_SAVED', flush=True)
