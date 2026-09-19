"""Produce clean FineSkin layers, a stable rest atlas and eligible wound surfaces.

Texture baking is asset production. No preview or gameplay test is performed.
"""
import bpy, json
from pathlib import Path
from mathutils import Vector

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets')
SOURCE = ROOT/'ZombieDogFineSkinV3/ZombieDog_FineSkin_Authoring.blend'
OUT = ROOT/'ZombieDogRandomWoundsV4'
(OUT/'Textures').mkdir(parents=True, exist_ok=True)
BOUNDS_MIN = (-25., -115., -5.)
BOUNDS_RANGE = (50., 210., 115.)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
rig.data.pose_position = 'REST'
mesh = obj.data
world = obj.matrix_world.copy()

def canonical(p):
    return Vector((p.x*100., -p.y*100., p.z*100.))

def region(p, n):
    # Centre eligibility leaves a margin around muzzle, paws, tail and belly.
    if p.y > 49 or p.y < -38 or p.z < 28 or n.z < -.45:
        return None
    if p.z < 45:
        return (6 if p.x > 0 else 7) if abs(p.x) > 6 else None
    if p.y > 38:
        return 4 if p.z > 55 else None
    if n.z > .60:
        return 5
    if abs(n.x) < .35:
        return None
    if p.y > 19:
        return 2 if p.x > 0 else 3
    return 0 if p.x > 0 else 1

mesh.calc_loop_triangles()
surfaces = []
normal_matrix = world.to_3x3().inverted().transposed()
for tri in mesh.loop_triangles:
    if tri.material_index != 0:
        continue
    source = [world @ mesh.vertices[i].co for i in tri.vertices]
    vertices = [canonical(p) for p in source]
    n0 = (normal_matrix @ tri.normal).normalized()
    normal = Vector((n0.x, -n0.y, n0.z))
    centre = sum(vertices, Vector())/3
    zone = region(centre, normal)
    if zone is None or any(region(p, normal) is None for p in vertices):
        continue
    area = (vertices[1]-vertices[0]).cross(vertices[2]-vertices[0]).length * .5
    if area < .0001:
        continue
    surfaces.append(dict(a=list(vertices[0]), b=list(vertices[1]), c=list(vertices[2]),
                         normal=list(normal), area=area, region=zone))
if not surfaces:
    raise RuntimeError('No eligible body surface could be authored')
(OUT/'wound_surfaces.json').write_text(json.dumps(dict(
    coordinates='rest cm: +X anatomical left, +Y muzzle, +Z up',
    bounds_min=BOUNDS_MIN, bounds_range=BOUNDS_RANGE, surfaces=surfaces), indent=2), encoding='utf-8')

# Copy the body graph for every section, including the ear cap. Fixed ear scarring
# belongs to the runtime material; all colour/normal layers here must be clean.
source_material = mesh.materials[0]
defs = []
for i in range(len(mesh.materials)):
    material = source_material.copy()
    material.name = ['M_ZombieDog_RandomBody_Source', 'M_ZombieDog_RandomFur_Source',
                     'M_ZombieDog_RandomEar_Source'][i]
    mesh.materials[i] = material
    ns = material.node_tree.nodes; lk = material.node_tree.links
    bs = next(n for n in ns if n.type == 'BSDF_PRINCIPLED')
    output = next(n for n in ns if n.type == 'OUTPUT_MATERIAL')
    base = bs.inputs['Base Color'].links[0].from_node
    skin_wound = base.inputs[2].links[0].from_node
    exposure = ns.new('ShaderNodeValue'); exposure.name = 'RuntimeExposureBake'; exposure.outputs[0].default_value = 0
    wound = ns.new('ShaderNodeValue'); wound.name = 'CleanWoundBake'; wound.outputs[0].default_value = 0
    for old, replacement in [(base.inputs[0].links[0].from_socket, exposure.outputs[0]),
                             (skin_wound.inputs[0].links[0].from_socket, wound.outputs[0])]:
        for link in list(old.links):
            destination = link.to_socket
            lk.remove(link); lk.new(replacement, destination)
    original = next(n for n in ns if n.type == 'TEX_IMAGE' and n.image and 'T_WolfDark_BaseColorAlpha' in n.image.name)
    skin_rough = next(n for n in ns if n.type == 'MAP_RANGE' and abs(n.inputs['To Min'].default_value-.54) < .001)
    skin_ao_tex = next(n for n in ns if n.type == 'TEX_IMAGE' and n.image and 'ZombieSkinMaterial1_ambientocclusion' in n.image.name)
    skin_ao = next(n for n in ns if n.type == 'MIX_RGB' and n.inputs[2].is_linked and
                   n.inputs[2].links[0].from_node == skin_ao_tex)
    data = ns.new('ShaderNodeCombineColor')
    lk.new(original.outputs['Alpha'], data.inputs['Red'])
    lk.new(skin_rough.outputs[0], data.inputs['Green'])
    lk.new(skin_ao.outputs[0], data.inputs['Blue'])
    rest = next(n for n in ns if n.type == 'ATTRIBUTE' and n.attribute_name == 'ZombieRestPosition')
    def vector_math(operation, a, b):
        n = ns.new('ShaderNodeVectorMath'); n.operation = operation
        lk.new(a, n.inputs[0]); n.inputs[1].default_value = b
        return n.outputs['Vector']
    p = vector_math('MULTIPLY', rest.outputs['Vector'], (100, -100, 100))
    p = vector_math('SUBTRACT', p, BOUNDS_MIN)
    p = vector_math('DIVIDE', p, BOUNDS_RANGE)
    defs.append((material, bs, output, exposure, dict(
        CoatBase=base.inputs[1].links[0].from_socket,
        SkinBase=skin_wound.inputs[1].links[0].from_socket,
        SurfaceData=data.outputs[0], RestPosition=p)))

bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True)
bpy.context.view_layer.objects.active = obj
mesh.uv_layers.active = mesh.uv_layers['ZombieUV']; mesh.uv_layers['ZombieUV'].active_render = True
scene = bpy.context.scene; scene.render.engine = 'CYCLES'; scene.cycles.samples = 8
scene.render.bake.margin = 24; scene.render.bake.use_clear = True
scene.render.bake.use_selected_to_active = False
files = {}
for semantic in ['CoatBase', 'SkinBase', 'SurfaceData', 'CoatNormal', 'SkinNormal', 'RestPosition']:
    is_normal = semantic.endswith('Normal'); is_position = semantic == 'RestPosition'
    size = 2048 if is_position else 4096
    image = bpy.data.images.new('T_ZombieDog_Random_'+semantic, size, size, alpha=False, float_buffer=is_position)
    image.colorspace_settings.name = 'sRGB' if semantic.endswith('Base') else 'Non-Color'
    temporary = []
    for material, bs, output, exposure, sockets in defs:
        ns = material.node_tree.nodes; lk = material.node_tree.links
        exposure.outputs[0].default_value = 1 if semantic == 'SkinNormal' else 0
        target = ns.new('ShaderNodeTexImage'); target.image = image; ns.active = target
        if not is_normal:
            em = ns.new('ShaderNodeEmission'); lk.new(sockets[semantic], em.inputs['Color'])
            lk.new(em.outputs[0], output.inputs['Surface']); temporary.append((material, em))
    if is_normal:
        bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', normal_r='POS_X', normal_g='NEG_Y', normal_b='POS_Z')
    else:
        bpy.ops.object.bake(type='EMIT')
    for material, em in temporary:
        material.node_tree.nodes.remove(em)
    for material, bs, output, exposure, _ in defs:
        material.node_tree.links.new(bs.outputs[0], output.inputs['Surface'])
        exposure.outputs[0].default_value = 0
    filename = OUT/'Textures'/(image.name+('.exr' if is_position else '.png'))
    if is_position:
        scene.render.image_settings.file_format = 'OPEN_EXR'
        scene.render.image_settings.color_depth = '16'
        scene.render.image_settings.color_mode = 'RGB'
        image.save_render(str(filename), scene=scene)
    else:
        image.filepath_raw = str(filename); image.file_format = 'PNG'; image.save()
    files[semantic] = str(filename)
    print('ZOMBIE_DOG_RANDOM_LAYER_BAKED', semantic, flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ZombieDog_RandomWounds_Authoring.blend'))
(OUT/'authoring_manifest.json').write_text(json.dumps(dict(source=str(SOURCE), textures=files,
    surface_triangles=len(surfaces), bounds_min=BOUNDS_MIN, bounds_range=BOUNDS_RANGE,
    mesh_reused='/Game/Monsters/ZombieDog/FineSkinV3/SK_ZombieDog_FineSkin',
    runtime_tested=False, preview_rendered=False), indent=2), encoding='utf-8')
print('ZOMBIE_DOG_RANDOM_WOUNDS_AUTHORED', flush=True)
