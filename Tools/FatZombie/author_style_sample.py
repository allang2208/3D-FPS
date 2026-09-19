"""Bake an infected-skin style sample on the existing Meshy UVs.

Blender authoring and texture baking only: no preview rendering, mesh export,
animation change or self-test. The original source and its materials are retained.
"""
import json
from pathlib import Path
import bpy

PROJECT = Path(__file__).resolve().parents[2]
OUT = PROJECT / 'SourceAssets/FatZombieStyleV1'
P = json.loads((OUT / 'style_parameters.json').read_text(encoding='utf-8'))
TEX = OUT / 'Textures'
TEX.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(PROJECT / P['source_blend']))
scene = bpy.context.scene
meshes = [o for o in scene.objects if o.type == 'MESH'
          and any(m.type == 'ARMATURE' for m in o.modifiers)]
for rig in [o for o in scene.objects if o.type == 'ARMATURE']:
    rig.data.pose_position = 'REST'
for obj in scene.objects:
    if obj.type == 'MESH' and obj not in meshes:
        obj.hide_render = True
bpy.context.view_layer.update()

material = bpy.data.materials.new('M_FatZombie_InfectedStyle_Authoring_V1')
material.use_nodes = True
nodes = material.node_tree.nodes
links = material.node_tree.links
nodes.clear()

def node(kind, label=''):
    n = nodes.new(kind)
    if label: n.label = label
    return n

def value(socket, v):
    if isinstance(v, bpy.types.NodeSocket):
        links.new(v, socket)
    else:
        if socket.type == 'RGBA' and isinstance(v, (int, float)): v = (v, v, v, 1)
        socket.default_value = v

def math(op, a, b=None):
    n = node('ShaderNodeMath')
    n.operation = op
    value(n.inputs[0], a)
    if b is not None: value(n.inputs[1], b)
    return n.outputs[0]

def mul(a, b): return math('MULTIPLY', a, b)
def add(a, b): return math('ADD', a, b)
def sub(a, b): return math('SUBTRACT', a, b)
def inv(a): return sub(1.0, a)

def ramp(a, low, high, minimum=0.0, maximum=1.0, label=''):
    n = node('ShaderNodeMapRange', label)
    n.clamp = True
    n.interpolation_type = 'SMOOTHSTEP'
    for socket, v in [('Value', a), ('From Min', low), ('From Max', high),
                      ('To Min', minimum), ('To Max', maximum)]:
        value(n.inputs[socket], v)
    return n.outputs[0]

def mix(a, b, factor, label=''):
    n = node('ShaderNodeMixRGB', label)
    for i, v in enumerate([factor, a, b]): value(n.inputs[i], v)
    return n.outputs[0]

def color_mul(a, b):
    n = node('ShaderNodeMixRGB')
    n.blend_type = 'MULTIPLY'
    value(n.inputs[0], 1.0)
    value(n.inputs[1], a)
    value(n.inputs[2], b)
    return n.outputs[0]

position = node('ShaderNodeNewGeometry', 'Metres in source rest pose').outputs['Position']
coords = node('ShaderNodeTexCoord')

def noise(scale, detail=2.0, vector=position, label=''):
    n = node('ShaderNodeTexNoise', label)
    value(n.inputs['Vector'], vector)
    n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = detail
    n.inputs['Roughness'].default_value = .55
    return n.outputs['Fac']

def texture(path, color=False, vector=None, box=False):
    n = node('ShaderNodeTexImage', Path(path).stem)
    n.image = bpy.data.images.load(str(path), check_existing=True)
    n.image.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
    if vector: value(n.inputs['Vector'], vector)
    if box:
        n.projection = 'BOX'
        n.projection_blend = .35
    return n.outputs['Color']

source = PROJECT / 'SourceAssets/FatZombieMeshy20260913/sources/meshy'
prefix = 'Meshy_AI_Mutant_Zombie_Charact_biped_texture_0'
base = texture(source / (prefix + '.png'), True, coords.outputs['UV'])
old_normal = texture(source / (prefix + '_normal.png'), False, coords.outputs['UV'])
old_rough = texture(source / (prefix + '_roughness.png'), False, coords.outputs['UV'])
gray = node('ShaderNodeRGBToBW')
value(gray.inputs[0], base)
luminance = gray.outputs[0]
hsv = node('ShaderNodeSeparateColor', 'Keep cloth, teeth, eyes out of skin pass')
hsv.mode = 'HSV'
value(hsv.inputs[0], base)
hue, sat = hsv.outputs[0], hsv.outputs[1]
skin = mul(mul(ramp(hue, .075, .105), inv(ramp(hue, .40, .48))), ramp(sat, .10, .26))
yellow = mul(skin, mul(inv(ramp(hue, .155, .215)), ramp(sat, .30, .58)))

broad = noise(8.0, 3.0, label='Centimetre-scale skin mottling')
medium = noise(39.0, 2.5, label='Break up former yellow paint patches')
fine = noise(190.0)
pores = noise(820.0, 1.5)

projection = node('ShaderNodeVectorMath')
projection.operation = 'SCALE'
value(projection.inputs[0], position)
projection.inputs[3].default_value = P['skin_detail_repeat_per_metre']
library = PROJECT / P['skin_library']
lib_height = texture(library / 'T_ZombieSkinMaterial1_height.png', vector=projection.outputs[0], box=True)
lib_rough = texture(library / 'T_ZombieSkinMaterial1_roughness.png', vector=projection.outputs[0], box=True)
lib_ao = texture(library / 'T_ZombieSkinMaterial1_ambientocclusion.png', vector=projection.outputs[0], box=True)

# Local lesions use the original rest surface. Baking makes them follow the skin
# rather than swimming through animated world-space procedural coordinates.
lesion_field = 0.0
for wound in P['large_wounds']:
    delta = node('ShaderNodeVectorMath'); delta.operation = 'SUBTRACT'
    value(delta.inputs[0], position); value(delta.inputs[1], tuple(wound['center']))
    scaled = node('ShaderNodeVectorMath'); scaled.operation = 'MULTIPLY'
    value(scaled.inputs[0], delta.outputs[0])
    value(scaled.inputs[1], tuple(1.0 / r for r in wound['radii']))
    length = node('ShaderNodeVectorMath'); length.operation = 'LENGTH'
    value(length.inputs[0], scaled.outputs[0])
    irregular = add(length.outputs['Value'], mul(sub(medium, .5), .30))
    field = inv(ramp(irregular, .58, 1.07))
    lesion_field = math('MAXIMUM', lesion_field, field)
lesion_field = mul(skin, lesion_field)
exposed = ramp(lesion_field, .35, .82)
rim = mul(mul(ramp(lesion_field, .06, .33), inv(ramp(lesion_field, .43, .73))),
          ramp(fine, .30, .65))
small_pus = mul(mul(yellow, ramp(medium, .59, .74)), inv(exposed))
dry_patches = mul(mul(yellow, ramp(medium, .44, .60)), mul(inv(small_pus), .34))
scab = math('MAXIMUM', rim, dry_patches)
wet = math('MAXIMUM', mul(exposed, ramp(fine, .24, .70, .66, 1.0)), small_pus)

tone = ramp(luminance, .022, .30, .62, 1.12)
skin_color = color_mul(mix(P['skin_color_low'], P['skin_color_high'], broad), tone)
skin_color = mix(skin_color, P['inflamed_color'], mul(yellow, .30), 'Subdued inflammation')
vein_cells = node('ShaderNodeTexVoronoi', 'Subtle dermal vascular mottling')
vein_cells.feature = 'DISTANCE_TO_EDGE'
value(vein_cells.inputs['Vector'], position)
vein_cells.inputs['Scale'].default_value = 33.0
veins = mul(inv(ramp(vein_cells.outputs['Distance'], .009, .031)), mul(yellow, .13))
skin_color = mix(skin_color, (.11, .066, .073, 1), veins)
skin_color = mix(skin_color, mix(P['tissue_color_low'], P['tissue_color_high'], fine), exposed)
skin_color = mix(skin_color, mix(P['scab_color_low'], P['scab_color_high'], lib_height), scab)
skin_color = mix(skin_color, mix(P['pus_color_low'], P['pus_color_high'], fine), small_pus)
cloth_color = color_mul(mix(base, luminance, .13), .86)
color = mix(cloth_color, skin_color, skin, 'Cloth and eyes retain their authored identity')

skin_rough = ramp(lib_rough, .05, .95, *P['skin_roughness'])
cloth_rough = ramp(old_rough, .05, .95, *P['cloth_roughness'])
rough = mix(cloth_rough, skin_rough, skin)
rough = mix(rough, ramp(fine, .1, .9, *P['scab_roughness']), scab)
rough = mix(rough, ramp(fine, .1, .9, *P['wet_roughness']), wet)
ao = mix(1.0, ramp(lib_ao, .0, 1.0, .92, 1.0), skin)

normal_map = node('ShaderNodeNormalMap', 'Preserve original anatomical normal')
normal_map.inputs['Strength'].default_value = P['source_normal_strength']
value(normal_map.inputs['Color'], old_normal)
surface = normal_map.outputs['Normal']
for label, height, strength, distance in [
    ('Shallow library relief', lib_height, mul(skin, .40), P['skin_relief_metres']),
    ('Tissue and scab edge', add(mul(scab, .4), sub(small_pus, mul(exposed, .65))), .52, P['lesion_relief_metres']),
    ('Fine skin pores', pores, mul(skin, .17), P['pore_relief_metres'])]:
    bump = node('ShaderNodeBump', label)
    value(bump.inputs['Normal'], surface); value(bump.inputs['Height'], height)
    value(bump.inputs['Strength'], strength); bump.inputs['Distance'].default_value = distance
    surface = bump.outputs['Normal']

bs = node('ShaderNodeBsdfPrincipled')
value(bs.inputs['Base Color'], color); value(bs.inputs['Roughness'], rough)
value(bs.inputs['Normal'], surface)
bs.inputs['Metallic'].default_value = 0.0
bs.inputs['Specular IOR Level'].default_value = .30
output = node('ShaderNodeOutputMaterial')
value(output.inputs['Surface'], bs.outputs[0])

packed = node('ShaderNodeCombineColor', 'AO / Roughness / Metallic')
value(packed.inputs[0], ao); value(packed.inputs[1], rough); value(packed.inputs[2], 0.0)
masks = node('ShaderNodeCombineColor', 'Skin / Wet tissue / Dry scab')
value(masks.inputs[0], skin); value(masks.inputs[1], wet); value(masks.inputs[2], scab)

for obj in meshes:
    for i in range(len(obj.data.materials)): obj.data.materials[i] = material
    obj.data.uv_layers.active.active_render = True

scene.render.engine = 'CYCLES'
scene.cycles.samples = 8
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
for device in prefs.devices: device.use = device.type != 'CPU'
scene.cycles.device = 'GPU'
scene.render.bake.margin = 24
scene.render.bake.use_selected_to_active = False
scene.render.bake.use_clear = False

outputs = {'BaseColor': color, 'ORM': packed.outputs[0], 'TissueMasks': masks.outputs[0], 'Normal': None}
files = {}
for semantic, socket in outputs.items():
    image = bpy.data.images.new('T_FatZombie_StyleV1_' + semantic, P['texture_size'], P['texture_size'], alpha=False)
    image.colorspace_settings.name = 'sRGB' if semantic == 'BaseColor' else 'Non-Color'
    image.generated_color = (0.5, 0.5, 1, 1) if semantic == 'Normal' else (0, 0, 0, 1)
    target = node('ShaderNodeTexImage', 'Bake target ' + semantic); target.image = image
    nodes.active = target
    emission = None
    if socket is not None:
        emission = node('ShaderNodeEmission'); value(emission.inputs['Color'], socket)
        value(output.inputs['Surface'], emission.outputs[0])
    else: value(output.inputs['Surface'], bs.outputs[0])
    for obj in meshes:
        bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        if semantic == 'Normal':
            bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', normal_r='POS_X', normal_g='NEG_Y', normal_b='POS_Z')
        else: bpy.ops.object.bake(type='EMIT')
    if emission: nodes.remove(emission)
    value(output.inputs['Surface'], bs.outputs[0])
    image.filepath_raw = str(TEX / (image.name + '.png'))
    image.file_format = 'PNG'; image.save()
    files[semantic] = image.filepath_raw
    print('FAT_STYLE_BAKED ' + semantic, flush=True)

material['style_revision'] = P['revision']
material['color_space'] = 'Linear RGB authoring; BaseColor baked to sRGB; normal is DirectX'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'FatZombie_StyleV1_Authoring.blend'))
(OUT / 'authoring_manifest.json').write_text(json.dumps({
    'source': P['source_blend'], 'parameters': P, 'textures': files,
    'authoring': str(OUT / 'FatZombie_StyleV1_Authoring.blend'),
    'library': P['skin_library'], 'channels': {'ORM': ['ao', 'roughness', 'metallic'],
    'TissueMasks': ['skin', 'wet', 'scab']},
    'scope': 'Material authoring only; existing mesh, UV, rig, animations and AI retained',
    'preview_rendered': False, 'runtime_tested': False}, indent=2), encoding='utf-8')
print('FAT_STYLE_AUTHORING_COMPLETE', flush=True)
