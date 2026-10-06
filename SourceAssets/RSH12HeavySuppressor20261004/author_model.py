"""Author an RSH-only game exterior inspired by the existing ASH accessory.

No UE import, gameplay changes, render, or verification pass. Construction
geometry, independent finish maps, and exports are written in this folder.
"""
import json
import math
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Quaternion, Vector

O = Path(__file__).resolve().parent
S = O.parent
T = O / 'Textures'
E = O / 'Exports'
T.mkdir(exist_ok=True)
E.mkdir(exist_ok=True)
LENGTH = .180
SEGMENTS = 144
TEXTURE_SIZE = 2048
MODEL = 'SM_RSH12_HeavySuppressor'
raw = json.loads((S / 'RSH12Integration20261003/canonical_parts.json').read_text(encoding='utf8'))
finish = json.loads((S / 'RSH12Optics20261004/finish_reference.json').read_text(encoding='utf8'))

# The front annulus of source part 3_l defines the visual contact boundary.
# No inferred whole-gun bounding box or sight-line origin is used.
barrel = np.asarray(next(p['verts'] for p in raw if p['name'] == '3_l'))
front = barrel[barrel[:, 1] < barrel[:, 1].min() + .00004]
center_xz = (front[:, (0, 2)].min(0) + front[:, (0, 2)].max(0)) * .5
radius = np.linalg.norm(front[:, (0, 2)] - center_xz, axis=1)
outer = np.unique(np.round(front[radius > .0085], 9), axis=0)
pivot = np.array([center_xz[0], outer[:, 1].mean(), center_xz[1]])
angles = np.arctan2(outer[:, 2] - pivot[2], outer[:, 0] - pivot[0]) % math.tau
outer = outer[np.argsort(angles)]
angles = np.sort(angles)
# x forward on the accessory maps to -Y on the original RSH model.
to_gun = Matrix(((0, 1, 0, float(pivot[0])),
                 (-1, 0, 0, float(pivot[1])),
                 (0, 0, 1, float(pivot[2])),
                 (0, 0, 0, 1)))
from_gun = to_gun.inverted()

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
output = bpy.data.collections.new('GAME_Export')
scene.collection.children.link(output)
construction = bpy.data.collections.new('EDITABLE_Construction')
scene.collection.children.link(construction)
guides = bpy.data.collections.new('INTERFACE_Guides')
scene.collection.children.link(guides)
parts = []
specs = []
maps = {}
materials = {}


def smooth(a, b, x):
    w = np.clip((x-a) / (b-a), 0., 1.)
    return w*w*(3.-2.*w)


def groove(x, theta):
    angle = (theta + math.pi/8) % (math.pi/4) - math.pi/8
    along = np.maximum(np.abs(x-.114)-.036, 0.)
    distance = np.sqrt(along*along + (.025*angle)**2) - .0038
    return 1. - smooth(-.0005, .0005, distance)


def contact(theta):
    """Intersect a radial line with the source outer polygon, preserving corners."""
    direction = np.array([math.cos(theta), math.sin(theta)])
    i = int(np.searchsorted(angles, theta % math.tau) - 1) % len(outer)
    a = outer[i, (0, 2)] - center_xz
    b = outer[(i+1) % len(outer), (0, 2)] - center_xz
    edge = b-a
    cross = lambda p, q: p[0]*q[1]-p[1]*q[0]
    radius_at = cross(a, edge) / cross(direction, edge)
    t = float(np.dot(direction*radius_at-a, edge)/np.dot(edge, edge))
    y = outer[i, 1]*(1-t) + outer[(i+1) % len(outer), 1]*t
    return float(radius_at), float(-(y-pivot[1]))


def save_image(name, rgb, srgb=False):
    h, w = rgb.shape[:2]
    image = bpy.data.images.new(name, width=w, height=h, alpha=True)
    image.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
    pixels = np.ones((h, w, 4), dtype=np.float32)
    pixels[:, :, :3] = rgb
    image.pixels.foreach_set(pixels.ravel())
    image.filepath_raw = str(T / (name + '.png'))
    image.file_format = 'PNG'
    image.save()
    return image


def make_material(name, color, roughness, metallic, profile=None):
    size = TEXTURE_SIZE
    v, u = np.mgrid[0:size, 0:size].astype(np.float32) / size
    rng = np.random.default_rng(127040 + len(materials))
    grain = rng.random((size, size), dtype=np.float32) - .5
    # Only fine machining texture; no old ASH low-frequency color mottling.
    height = grain*.0000006 + np.sin(v*math.tau*256.)*.0000002
    base = np.asarray(color, dtype=np.float32)[None, None, :] * (1+grain[:, :, None]*.015)
    base = np.where(base <= .0031308, base*12.92, 1.055*np.maximum(base, 0)**(1/2.4)-.055)
    r = np.clip(roughness + grain*.012, .05, .95)
    ao = np.ones_like(r)
    if profile is not None:
        distances = np.concatenate(([0.], np.cumsum(np.linalg.norm(np.diff(profile, axis=0), axis=1))))
        x = np.interp(u, distances/distances[-1], np.asarray(profile)[:, 0])
        ao -= .12*groove(x, v*math.tau)
    color_map = save_image('T_RSH12_Heavy_' + name + '_BaseColor', np.clip(base, 0, 1), True)
    orm_map = save_image('T_RSH12_Heavy_' + name + '_ORM', np.stack((ao, r, np.full_like(r, metallic)), axis=-1))
    dx = (np.roll(height, -1, 1)-np.roll(height, 1, 1))/(2*LENGTH/size)
    dy = (np.roll(height, -1, 0)-np.roll(height, 1, 0))/(2*math.pi*.052/size)
    normal = np.stack((-dx, -dy, np.ones_like(dx)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    gl_map = save_image('T_RSH12_Heavy_' + name + '_NormalGL', normal*.5+.5)
    normal[:, :, 1] *= -1
    dx_map = save_image('T_RSH12_Heavy_' + name + '_NormalDX', normal*.5+.5)
    mat = bpy.data.materials.new('RSH12Heavy_' + name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    color_node = nodes.new('ShaderNodeTexImage'); color_node.image = color_map
    packed_node = nodes.new('ShaderNodeTexImage'); packed_node.image = orm_map
    separate = nodes.new('ShaderNodeSeparateColor')
    links.new(color_node.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(packed_node.outputs['Color'], separate.inputs['Color'])
    links.new(separate.outputs['Green'], bsdf.inputs['Roughness'])
    links.new(separate.outputs['Blue'], bsdf.inputs['Metallic'])
    normal_node = nodes.new('ShaderNodeTexImage'); normal_node.image = gl_map
    normal_map = nodes.new('ShaderNodeNormalMap'); normal_map.uv_map = 'UV0'
    links.new(normal_node.outputs['Color'], normal_map.inputs['Color'])
    links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])
    materials[name] = mat
    maps[name] = dict(base_color=str(Path(color_map.filepath_raw).relative_to(O)),
                      orm=str(Path(orm_map.filepath_raw).relative_to(O)),
                      normal_dx=str(Path(dx_map.filepath_raw).relative_to(O)),
                      normal_gl=str(Path(gl_map.filepath_raw).relative_to(O)),
                      linear_base_color=list(color), roughness=roughness, metallic=metallic)
    return mat


body_profile = [(.048, 0), (.048, .0240), (.049, .0245), (.052, .0250)]
body_profile += [(float(x), .0250) for x in np.linspace(.056, .165, 72)]
body_profile += [(.168, .025), (.171, .0249), (.174, .0245), (.176, .0237),
                 (.1785, .0223), (.1796, .0217), (.180, .0212),
                 (.180, .0080), (.1795, .0074), (.168, .0074), (.168, 0)]
make_material('Shell', finish['base_color'], float(finish['roughness'][0]), 1., body_profile)
make_material('Band', (.066, .057, .042), .43, 1.)
make_material('Mount', tuple(c*.82 for c in finish['base_color']), .42, 1.)
inner = bpy.data.materials.new('RSH12Heavy_Inner')
inner.use_nodes = True
inner.diffuse_color = (.005, .0055, .006, 1)
inner.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = inner.diffuse_color
inner.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .92
inner.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value = 0.
materials['Inner'] = inner


def revolved(name, profile, region, deform=None, region_strip=None, closed=False):
    profile = np.asarray(profile, dtype=float)
    distances = np.concatenate(([0.], np.cumsum(np.linalg.norm(np.diff(profile, axis=0), axis=1))))
    if closed:
        total = distances[-1] + float(np.linalg.norm(profile[-1]-profile[0]))
    else:
        total = distances[-1]
    rings, vertices, faces, coords, regions = [], [], [], [], []
    for i, (x, r) in enumerate(profile):
        if r == 0:
            rings.append([len(vertices)]); vertices.append((float(x), 0, 0))
            continue
        indices = []
        for j in range(SEGMENTS):
            theta = math.tau*j/SEGMENTS
            px, pr = deform(float(x), float(r), theta) if deform else (x, r)
            indices.append(len(vertices))
            vertices.append((float(px), float(pr)*math.cos(theta), float(pr)*math.sin(theta)))
        rings.append(indices)
    strip_count = len(profile) if closed else len(profile)-1
    for i in range(strip_count):
        next_i = (i+1) % len(profile)
        a, b = rings[i], rings[next_i]
        ua, ub = distances[i]/total, (distances[next_i]/total if next_i else 1.)
        section = region_strip(i) if region_strip else region
        for j in range(SEGMENTS):
            k = (j+1) % SEGMENTS
            if len(a) == 1:
                face = (a[0], b[k], b[j])
            elif len(b) == 1:
                face = (a[j], a[k], b[0])
            else:
                face = (a[j], a[k], b[k], b[j])
            if len(a) == 1 or len(b) == 1:
                # Planar caps retain finite UV area at the center vertex.
                max_r = max(profile[i, 1], profile[next_i, 1])
                uv = [(vertices[index][1]/(2*max_r)+.5, vertices[index][2]/(2*max_r)+.5) for index in face]
            else:
                uv = [(ua, j/SEGMENTS), (ua, (j+1)/SEGMENTS), (ub, (j+1)/SEGMENTS), (ub, j/SEGMENTS)]
            faces.append(face); coords.append(uv); regions.append(section)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces); mesh.update()
    for material in materials.values(): mesh.materials.append(material)
    region_names = list(materials)
    uv = mesh.uv_layers.new(name='UV0')
    for poly, values, material_name in zip(mesh.polygons, coords, regions):
        poly.material_index = region_names.index(material_name)
        poly.use_smooth = True
        for loop, xy in zip(poly.loop_indices, values): uv.data[loop].uv = xy
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh); bm.free()
    # Separate broad end faces from cylindrical shading at steep junctions.
    edge_normals = {}
    for poly in mesh.polygons:
        for edge in poly.edge_keys: edge_normals.setdefault(tuple(sorted(edge)), []).append(poly.normal.copy())
    for edge in mesh.edges:
        normals = edge_normals.get(tuple(sorted(edge.vertices)), [])
        edge.use_edge_sharp = len(normals) == 2 and normals[0].dot(normals[1]) < math.cos(math.radians(50))
    obj = bpy.data.objects.new(name, mesh)
    output.objects.link(obj)
    parts.append(obj)
    specs.append(dict(name=name, region=region, profile_m=profile.tolist()))
    return obj


def shell_shape(x, r, theta):
    return x, r-.00125*float(groove(x, theta)) if .055 < x < .168 and r > .020 else r


revolved('FlutedBody', body_profile, 'Shell', shell_shape,
         lambda i: 'Inner' if i >= len(body_profile)-4 else 'Shell')

# The rear face starts with the source 18-sided annulus and blends to the
# new round exterior. There are no thread specifications or internal parts.
contact_radius = float(np.linalg.norm(outer[:, (0, 2)]-center_xz, axis=1).mean())
mount_profile = [(.006, 0), (.006, .0071), (0, .0071), (0, contact_radius),
                 (.001, contact_radius), (.003, .0100), (.005, .0108),
                 (.007, .0117), (.009, .0132), (.011, .0153), (.013, .0180),
                 (.015, .0207), (.017, .0230), (.019, .0247), (.022, .0247), (.022, 0)]


def mount_shape(x, r, theta):
    if r < .008:
        return x, r
    source_r, source_x = contact(theta)
    weight = 1-float(smooth(.001, .007, x))
    return x + source_x*weight, r + (source_r-contact_radius)*weight


revolved('RSH_ContourMount', mount_profile, 'Mount', mount_shape,
         lambda i: 'Inner' if i < 2 else 'Mount')

band_profile = [(.0195, 0), (.0195, .0244), (.0205, .0254), (.022, .0266), (.024, .027)]
band_profile += [(float(x), .027) for x in np.linspace(.025, .046, 28)]
band_profile += [(.0475, .0269), (.049, .0263), (.0505, .0253), (.052, .0246), (.052, 0)]


def band_shape(x, r, theta):
    if r < .022:
        return x, r
    fade = float(smooth(.022, .026, x)*(1-smooth(.044, .049, x)))
    return x, r-.00055*fade*(.5+.5*math.cos(36*(theta-(x-.025)*13)))


revolved('DiagonalTitaniumBand', band_profile, 'Band', band_shape)
revolved('RearDarkTrim', [(.0182, .0240), (.0186, .0250), (.0194, .0254),
                        (.0203, .0254), (.0208, .0251), (.0209, .0245),
                        (.020, .0239)], 'Mount', closed=True)
revolved('FrontDarkBezel', [(.1715, .0246), (.172, .0250), (.1726, .0252),
                          (.1737, .0250), (.1745, .0247), (.175, .0243),
                          (.1747, .0240), (.173, .0244)], 'Mount', closed=True)

# Keep separate, editable authored parts and an independent export mesh.
for obj in parts:
    source = obj.copy(); source.data = obj.data.copy(); source.name = 'SRC_' + obj.name
    construction.objects.link(source)
construction.hide_viewport = True
construction.hide_render = True
bpy.ops.object.select_all(action='DESELECT')
for obj in parts: obj.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
model = bpy.context.object
model.name = MODEL
scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
weighted = model.modifiers.new('MachinedSurfaceNormals', 'WEIGHTED_NORMAL')
weighted.keep_sharp = True
bpy.ops.object.modifier_apply(modifier=weighted.name)
triangulate = model.modifiers.new('ExportTriangles', 'TRIANGULATE')
triangulate.keep_custom_normals = True
bpy.ops.object.modifier_apply(modifier=triangulate.name)
model['ExclusiveWeapon'] = 'ue_rsh12'
model['ProposedOptionId'] = 'rsh12_heavy_suppressor'
model['SourceReference'] = 'ASH12TacticalSuppressor20260919; newly authored RSH exterior'
model['UnitContract'] = 'meters in Blender; FBX centimeter conversion once; +X forward, +Z up'
model['Interface'] = 'Original RSH 3_l muzzle annulus; no runtime attachment is installed'

for name, location in [('MountFace', (0, 0, 0)), ('MuzzleExit', (LENGTH, 0, 0))]:
    guide = bpy.data.objects.new(name, None); guide.empty_display_type = 'ARROWS'
    guide.empty_display_size = .012; guide.location = location
    guides.objects.link(guide)

fbx = E / (MODEL + '.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'MESH'},
                        axis_forward='-Y', axis_up='Z', use_mesh_modifiers=True,
                        bake_anim=False, add_leaf_bones=False, use_tspace=True,
                        mesh_smooth_type='FACE', path_mode='RELATIVE')
glb = E / (MODEL + '.glb')
bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', use_selection=True,
                         export_texcoords=True, export_normals=True, export_tangents=True,
                         export_materials='EXPORT')

# Pack only the newly authored textures in the editable accessory source.
for image in bpy.data.images:
    if image.source == 'FILE' and image.filepath:
        image.pack()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.region_3d.view_location = Vector((LENGTH*.5, 0, 0))
            area.spaces.active.region_3d.view_distance = .32
            area.spaces.active.clip_start = .001
            area.spaces.active.shading.color_type = 'MATERIAL'
blend = O / 'RSH12_HeavySuppressor_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))

# A separate placement source contains a clearly marked static reference gun.
# It is not a render, replacement weapon, or runtime export.
reference = bpy.data.collections.new('REFERENCE_RSH_Original_Static_DoNotExport')
scene.collection.children.link(reference)
reference_material = bpy.data.materials.new('REFERENCE_GunGrey')
reference_material.diffuse_color = (.095, .105, .115, 1)
for part in raw:
    if part['name'] == '10_l':
        continue
    vertices = [from_gun @ Vector(v) for v in part['verts']]
    mesh = bpy.data.meshes.new('REF_' + part['name'])
    mesh.from_pydata(vertices, [], part['faces']); mesh.update()
    mesh.materials.append(reference_material)
    uv = mesh.uv_layers.new(name='UV0')
    for item, value in zip(uv.data, part['uv']): item.uv = value
    for face in mesh.polygons: face.use_smooth = True
    mesh.normals_split_custom_set([(from_gun.to_3x3() @ Vector(n)).normalized() for n in part['normals']])
    obj = bpy.data.objects.new(mesh.name, mesh)
    reference.objects.link(obj)
    obj.hide_select = True
reference.hide_render = True
assembly = O / 'RSH12_HeavySuppressor_FitSource.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(assembly))

report = {
    'status': 'authored_and_exported', 'exclusive_weapon': 'ue_rsh12',
    'proposed_option_id': 'rsh12_heavy_suppressor', 'model': MODEL,
    'blend': str(blend), 'placement_source': str(assembly),
    'fbx': str(fbx), 'glb': str(glb),
    'art_scale_m': {'length': LENGTH, 'max_diameter': .054},
    'triangles': len(model.data.polygons), 'vertices': len(model.data.vertices),
    'material_slots': [m.name for m in model.data.materials],
    'parts': specs, 'texture_size': TEXTURE_SIZE, 'textures': maps,
    'finish_reference': finish,
    'interface': {
        'source_part': '3_l', 'source_plane': 'front outer annulus vertices',
        'source_outer_boundary_canonical_m': outer.tolist(),
        'pivot_canonical_m': pivot.tolist(),
        'accessory_to_canonical_m': [list(row) for row in to_gun],
        'local_axes': '+X forward / +Y right / +Z up',
        'mount_local_m': [0, 0, 0], 'muzzle_exit_local_m': [LENGTH, 0, 0],
        'runtime_mount_transform': 'Not installed; convert canonical frame through active RSH grip registration at integration',
    },
    'references': [
        'SourceAssets/ASH12TacticalSuppressor20260919/author_model.py',
        'SourceAssets/ASH12TacticalSuppressor20260919/ASH12_TacticalSuppressor_Editable.blend',
        'SourceAssets/RSH12Integration20261003/canonical_parts.json',
    ],
    'imported_to_ue': False, 'runtime_integrated': False,
    'rendered': False, 'tested': False,
}
(O / 'authoring.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
print('RSH_HEAVY_SUPPRESSOR_AUTHORED', json.dumps({
    'triangles': report['triangles'], 'materials': report['material_slots'],
    'fbx': str(fbx), 'glb': str(glb), 'blend': str(blend),
}), flush=True)
