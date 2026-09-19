"""Render the inventory icon for the battle axe: transparent background, level view, blade left.

Blender --background --python <this> -- <fitted.fbx> <texture.png> <normal.png> <roughness.png> <metallic.png> <out.png> [resolution]

The fitted FBX references a .fbm texture folder the ZIP does not ship, so the material is
rebuilt from the package's own PNG maps. Composition follows the retired icon: head upper
right, handle to lower left. Diagnostic render only.
"""
import bpy
import math
import sys
from pathlib import Path
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
axe, base, normal, rough, metal, out = (Path(args[0]), Path(args[1]), Path(args[2]),
                                        Path(args[3]), Path(args[4]), Path(args[5]))
resolution = int(args[6]) if len(args) > 6 else 512
out.parent.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(axe))
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']

material = bpy.data.materials.new('Axe_Icon')
material.use_nodes = True
nodes = material.node_tree.nodes
links = material.node_tree.links
bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
for socket, file, colorspace, is_data in [('Base Color', base, 'sRGB', False),
                                          ('Roughness', rough, 'Non-Color', True),
                                          ('Metallic', metal, 'Non-Color', True)]:
    image = bpy.data.images.load(str(file))
    image.colorspace_settings.name = colorspace
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = image
    if is_data:
        links.new(tex.outputs['Color'], bsdf.inputs[socket])
    else:
        links.new(tex.outputs['Color'], bsdf.inputs[socket])
normal_image = bpy.data.images.load(str(normal))
normal_image.colorspace_settings.name = 'Non-Color'
normal_tex = nodes.new('ShaderNodeTexImage')
normal_tex.image = normal_image
normal_map = nodes.new('ShaderNodeNormalMap')
links.new(normal_tex.outputs['Color'], normal_map.inputs['Color'])
links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])
for obj in meshes:
    obj.data.materials.clear()
    obj.data.materials.append(material)

# Icon composition follows the retired tool icon: head upper right with the blade facing right,
# handle running down to the lower left. The fitted mesh stands Z-up with the blade edge on +X;
# a positive Y rotation tips the head (+Z) toward +X so the tool leans the accepted way, and the
# camera looks along +Y so that +X reads as image-right.
for obj in meshes:
    obj.rotation_euler = (0.0, math.radians(38.0), 0.0)
bpy.context.view_layer.update()
points = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
lower = Vector(tuple(min(p[i] for p in points) for i in range(3)))
upper = Vector(tuple(max(p[i] for p in points) for i in range(3)))
centre = (lower + upper) * .5
span_x = upper.x - lower.x
span_y = upper.y - lower.y
span_z = upper.z - lower.z

scene = bpy.context.scene
engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in engines else 'BLENDER_EEVEE'
scene.render.resolution_x = resolution
scene.render.resolution_y = resolution
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.view_settings.view_transform = 'AgX'

camera_data = bpy.data.cameras.new('Icon')
camera_data.type = 'ORTHO'
camera_data.ortho_scale = max(span_x, span_z) / .84
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

scene.render.filepath = str(out)
bpy.ops.render.render(write_still=True)
print('ICON_RENDERED', out, flush=True)