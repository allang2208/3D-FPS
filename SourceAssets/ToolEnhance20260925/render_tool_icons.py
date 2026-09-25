"""Rebake the axe/pickaxe inventory icons at the factory enhancement level (L1 stone).

Blender --background --python render_tool_icons.py -- axe
Blender --background --python render_tool_icons.py -- pick

The world FBXs on disk are the split versions (materials Metal/Wood, geometry
unchanged).  Wood keeps the original PBR look; Metal approximates
MI_ToolHead_*_Stone: base color desaturated 85% and multiplied by the stone
tint, roughness scaled by 1.7, metallic forced to 0.  Camera, lights, world,
resolution and framing replicate the original icon scripts so the only visual
delta versus the shipped icons is the stone head.

Outputs: Icons/<name>.png plus a packed editable blend next to it.
"""
import bpy
import math
import sys
from pathlib import Path

from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'Icons'
OUT.mkdir(parents=True, exist_ok=True)

AXE_TEX = ROOT / 'SourceAssets/AxeImpactInventory20260919/Textures'
STONE_TINT = (0.42, 0.40, 0.37)
STONE_SATURATION = 0.15   # Desaturate 0.85 in the UE master
STONE_ROUGH_SCALE = 1.7

CONFIG = {
    'axe': {
        'fbx': ROOT / 'SourceAssets/BattleAxeReplace20260919/Fitted/BattleAxe_16000.fbx',
        'out': OUT / 'axe_upright.png',
        'width': 256,          # height = width * 3 (1x3 grid slot)
        'aspect': 1.0 / 3.0,
    },
    'pick': {
        'fbx': ROOT / 'SourceAssets/RusticPickaxe20260919/Export/RusticPickaxe_World.fbx',
        'out': OUT / 'pickaxe_upright.png',
        'width': 512,          # 512x768 (2x3 grid slot)
        'aspect': 2.0 / 3.0,
    },
}

target = sys.argv[sys.argv.index('--') + 1]
cfg = CONFIG[target]


def load_image(path, colorspace):
    image = bpy.data.images.load(str(path))
    image.colorspace_settings.name = colorspace
    return image


def make_material(name, kind, stone):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    nodes = tree.nodes
    links = tree.links
    bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')

    if kind == 'axe':
        base_img = load_image(AXE_TEX / 'Meshy_AI_Weathered_Battle_Axe_0918025738_texture.png', 'sRGB')
        normal_img = load_image(AXE_TEX / 'Meshy_AI_Weathered_Battle_Axe_0918025738_texture_normal.png', 'Non-Color')
        rough_img = load_image(AXE_TEX / 'Meshy_AI_Weathered_Battle_Axe_0918025738_texture_roughness.png', 'Non-Color')
        metal_img = load_image(AXE_TEX / 'Meshy_AI_Weathered_Battle_Axe_0918025738_texture_metallic.png', 'Non-Color')
        base_channel, rough_channel, metal_channel = 'Color', 'Color', 'Color'
    else:
        tex_dir = ROOT / 'SourceAssets/RusticPickaxe20260919/Textures'
        base_img = load_image(tex_dir / 'BaseColor.jpg', 'sRGB')
        normal_img = load_image(tex_dir / 'Normal.jpg', 'Non-Color')
        rough_img = load_image(tex_dir / 'MetallicRoughness.jpg', 'Non-Color')
        metal_img = rough_img
        base_channel, rough_channel, metal_channel = 'Color', 'Green', 'Blue'

    def tex_node(image):
        for n in nodes:
            if n.type == 'TEX_IMAGE' and n.image == image:
                return n
        n = nodes.new('ShaderNodeTexImage')
        n.image = image
        return n

    def channel(image, channel_name):
        src = tex_node(image)
        if channel_name == 'Color':
            return src.outputs['Color']
        sep = nodes.new('ShaderNodeSeparateColor')
        links.new(src.outputs['Color'], sep.inputs['Color'])
        return sep.outputs[channel_name]

    # Base color; stone slots additionally desaturate and tint like the UE master.
    base_out = channel(base_img, base_channel)
    if stone:
        hue = nodes.new('ShaderNodeHueSaturation')
        hue.inputs['Saturation'].default_value = STONE_SATURATION
        links.new(base_out, hue.inputs['Color'])
        mix = nodes.new('ShaderNodeMixRGB')
        mix.blend_type = 'MULTIPLY'
        mix.inputs['Color2'].default_value = STONE_TINT + (1.0,)
        links.new(hue.outputs['Color'], mix.inputs['Color1'])
        base_out = mix.outputs['Color']
    links.new(base_out, bsdf.inputs['Base Color'])

    # Roughness, stone scaled by 1.7 and clamped like RoughScale in the master.
    rough_out = channel(rough_img, rough_channel)
    if stone:
        mul = nodes.new('ShaderNodeMath')
        mul.operation = 'MULTIPLY'
        mul.inputs[1].default_value = STONE_ROUGH_SCALE
        links.new(rough_out, mul.inputs[0])
        # Clamp to 1 with MINIMUM (ShaderNodeClamp socket names differ in Blender 5.1).
        clamp = nodes.new('ShaderNodeMath')
        clamp.operation = 'MINIMUM'
        clamp.inputs[1].default_value = 1.0
        links.new(mul.outputs[0], clamp.inputs[0])
        rough_out = clamp.outputs[0]
    links.new(rough_out, bsdf.inputs['Roughness'])

    # Metallic: stone is a dielectric (MetallicConst 0); wood keeps the map.
    if stone:
        bsdf.inputs['Metallic'].default_value = 0.0
    else:
        links.new(channel(metal_img, metal_channel), bsdf.inputs['Metallic'])

    normal_tex = tex_node(normal_img)
    normal_map = nodes.new('ShaderNodeNormalMap')
    links.new(normal_tex.outputs['Color'], normal_map.inputs['Color'])
    links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(cfg['fbx']))
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
if not meshes:
    raise SystemExit('no mesh imported from ' + str(cfg['fbx']))

kind = 'axe' if target == 'axe' else 'pick'
materials = {'Wood': make_material('IconWood_' + target, kind, stone=False),
             'Metal': make_material('IconStone_' + target, kind, stone=True)}
for obj in meshes:
    for index, slot in enumerate(obj.material_slots):
        replacement = materials.get(slot.name)
        if replacement is None:
            raise SystemExit('unexpected slot %r on %s' % (slot.name, obj.name))
        slot.material = replacement

for obj in meshes:
    obj.rotation_euler = (0.0, 0.0, 0.0)
bpy.context.view_layer.update()
points = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
lower = Vector(tuple(min(p[i] for p in points) for i in range(3)))
upper = Vector(tuple(max(p[i] for p in points) for i in range(3)))
centre = (lower + upper) * .5
span_x = upper.x - lower.x
span_z = upper.z - lower.z

scene = bpy.context.scene
engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in engines else 'BLENDER_EEVEE'
scene.render.resolution_x = cfg['width']
scene.render.resolution_y = 768
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.view_settings.view_transform = 'AgX'

camera_data = bpy.data.cameras.new('Icon')
camera_data.type = 'ORTHO'
camera_data.sensor_fit = 'VERTICAL'
camera_data.ortho_scale = max(span_z / .92, span_x / (cfg['aspect'] * .90))
camera = bpy.data.objects.new('Icon', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera.location = (centre.x, centre.y - 6.0, centre.z)
camera.rotation_euler = (math.radians(90.0), 0.0, 0.0)

for name, location, energy in [('key', (2.5, -3.0, 3.5), 620), ('fill', (-3.0, -1.5, 1.2), 220),
                               ('rim', (0.5, 3.5, 2.5), 330)]:
    light_data = bpy.data.lights.new(name, 'AREA')
    light_data.energy = energy
    light_data.size = 3.0
    light = bpy.data.objects.new(name, light_data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (Vector(centre) - light.location).to_track_quat('-Z', 'Y').to_euler()

world = bpy.data.worlds.new('IconWorld')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.30, 0.31, 0.33, 1.0)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.8
scene.world = world

scene.render.filepath = str(cfg['out'])
for mat in materials.values():
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            node.image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(cfg['out'].with_suffix('.blend')))
bpy.ops.render.render(write_still=True)
print('ICON_RENDERED', target, cfg['out'], flush=True)
