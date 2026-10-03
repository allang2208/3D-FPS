"""Refine the installed default crystal with sub-mm edges and restrained growth.

Blender background production only. The frozen UE exports retain all non-quartz
geometry. No internal sheets, refraction geometry, scene rendering or gameplay.
"""
import bpy
import bmesh
import json
import math
import re
from pathlib import Path
from mathutils import Vector
import numpy as np

ROOT = Path(__file__).resolve().parent
P = json.loads((ROOT / 'parameters.json').read_text(encoding='utf-8'))
INPUT = json.loads((ROOT / 'inputs-receipt.json').read_text(encoding='utf-8'))
OUT = ROOT / 'Export'
TEX = OUT / 'Textures'
TEX.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT.parent / 'BarkRebuildV21/Staff_NaturalBark_V21.blend'
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)


def write_image(name, pixels):
    image = bpy.data.images.new(name, width=P['texture_size'], height=P['texture_size'], alpha=True)
    image.colorspace_settings.name = 'Non-Color'
    image.pixels.foreach_set(pixels.astype(np.float32).ravel())
    image.filepath_raw = str(TEX / (name + '.png'))
    image.file_format = 'PNG'
    image.save()
    image.pack()
    return image


def make_surface_maps():
    n = P['texture_size']
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
    rng = np.random.default_rng(P['seed'])
    growth = np.zeros((n, n), dtype=np.float32)
    pits = np.zeros_like(growth)
    # Fine longitudinal growth lines occupy a small part of each clean facet.
    for _ in range(11):
        center = rng.uniform(0, 1) + .0008 * np.sin(y * math.tau * rng.integers(2, 7) + rng.uniform(0, math.tau))
        distance = np.abs((x - center + .5) % 1 - .5)
        line = np.exp(-np.square(distance / rng.uniform(.0015, .003)))
        taper = np.square(.5 + .5 * np.sin(y * math.tau + rng.uniform(0, math.tau)))
        growth = np.maximum(growth, line * taper * rng.uniform(.25, .65))
    for _ in range(13):
        dx = ((x - rng.uniform(0, 1) + .5) % 1 - .5) / rng.uniform(.003, .008)
        dy = ((y - rng.uniform(0, 1) + .5) % 1 - .5) / rng.uniform(.0015, .005)
        pits = np.maximum(pits, np.exp(-(dx * dx + dy * dy)) * rng.uniform(.25, .7))
    height = growth * P['growth_height_cm'] - pits * P['pit_height_cm']
    du = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * (n / (2 * P['texture_u_cm']))
    dv = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * (n / (2 * P['texture_v_cm']))
    normals = np.stack((-du, -dv, np.ones_like(du)), axis=-1)
    normals /= np.linalg.norm(normals, axis=-1, keepdims=True)
    normal_rgba = np.concatenate((normals * .5 + .5, np.ones((n, n, 1))), axis=-1)
    surface_rgba = np.stack((growth, pits, np.zeros_like(growth), np.ones_like(growth)), axis=-1)
    return write_image('T_QuartzSurface_Normal_V35', normal_rgba), write_image('T_QuartzSurface_Masks_V35', surface_rgba)


normal_image, surface_image = make_surface_maps()


def create_quartz_material():
    mat = bpy.data.materials.new(P['material'])
    mat.use_nodes = True
    mat.diffuse_color = (*P['base_color'], 1)
    nodes = mat.node_tree.nodes
    nodes.clear()
    links = mat.node_tree.links
    out = nodes.new('ShaderNodeOutputMaterial')
    bs = nodes.new('ShaderNodeBsdfPrincipled')
    bs.inputs['Base Color'].default_value = (*P['transmittance_clear'], 1)
    bs.inputs['IOR'].default_value = P['ior']
    bs.inputs['Transmission Weight'].default_value = P['blender_transmission']
    links.new(bs.outputs[0], out.inputs['Surface'])
    vertex = nodes.new('ShaderNodeVertexColor')
    vertex.layer_name = 'QuartzSurface'
    separate = nodes.new('ShaderNodeSeparateColor')
    links.new(vertex.outputs['Color'], separate.inputs['Color'])
    rough = nodes.new('ShaderNodeMath')
    rough.operation = 'MULTIPLY_ADD'
    rough.inputs[1].default_value = P['roughness_max'] - P['roughness_min']
    rough.inputs[2].default_value = P['roughness_min']
    links.new(separate.outputs['Red'], rough.inputs[0])
    mask = nodes.new('ShaderNodeTexImage')
    mask.image = surface_image
    mask_separate = nodes.new('ShaderNodeSeparateColor')
    links.new(mask.outputs['Color'], mask_separate.inputs['Color'])
    for output, key in ((mask_separate.outputs['Red'], 'roughness_growth_add'),
                        (mask_separate.outputs['Green'], 'roughness_pit_add'),
                        (separate.outputs['Green'], 'roughness_bevel_add')):
        addition = nodes.new('ShaderNodeMath')
        addition.operation = 'MULTIPLY_ADD'
        addition.inputs[1].default_value = P[key]
        links.new(output, addition.inputs[0])
        links.new(rough.outputs[0], addition.inputs[2])
        rough = addition
    links.new(rough.outputs[0], bs.inputs['Roughness'])
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = normal_image
    normal = nodes.new('ShaderNodeNormalMap')
    links.new(tex.outputs['Color'], normal.inputs['Color'])
    links.new(normal.outputs['Normal'], bs.inputs['Normal'])
    # The author file uses true transmission. UE coverage is controlled in its
    # own recipe; a Blender preview is not a substitute for the game material.
    return mat


quartz_material = create_quartz_material()


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def filter_faces(obj, quartz):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    unwanted = [f for f in bm.faces if (obj.data.materials[f.material_index].name.startswith('M_Staff_Quartz') != quartz)]
    bmesh.ops.delete(bm, geom=unwanted, context='FACES')
    isolated = [v for v in bm.verts if not v.link_faces]
    if isolated:
        bmesh.ops.delete(bm, geom=isolated, context='VERTS')
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


manifest = []
objects = []
for entry in INPUT['meshes']:
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=entry['fbx'], use_custom_normals=True)
    imported = [o for o in bpy.context.scene.objects if o not in before and o.type == 'MESH']
    if len(imported) != 1:
        raise RuntimeError('Expected one installed mesh in ' + entry['fbx'])
    obj = imported[0]
    activate(obj)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # Restore the UE-centimetre author convention after FBX metre conversion.
    lo = Vector([min(v.co[i] for v in obj.data.vertices) for i in range(3)])
    hi = Vector([max(v.co[i] for v in obj.data.vertices) for i in range(3)])
    factor = entry['size_cm'][2] / (hi.z - lo.z)
    current_center = (lo + hi) * (.5 * factor)
    offset = Vector(entry['origin_cm']) - current_center
    for v in obj.data.vertices:
        v.co = v.co * factor + offset
    for i, slot in enumerate(entry['slots']):
        if not slot['material']:
            raise RuntimeError('Missing retained material slot on ' + entry['name'])
        obj.data.materials[i].name = slot['material'].split('.')[-1]
    retained_materials = list(obj.data.materials)
    # UE stores one vertex-colour channel. Keep retained non-quartz values in
    # that channel and ensure joining the new crystal cannot export a stale
    # white colour layer before the facet/bevel masks.
    previous_colors = obj.data.color_attributes.active_color
    retained_colors = [tuple(previous_colors.data[loop.vertex_index if previous_colors.domain == 'POINT' else loop.index].color)
                       if previous_colors else (1., 1., 1., 1.) for loop in obj.data.loops]
    for attribute in list(obj.data.color_attributes):
        obj.data.color_attributes.remove(attribute)
    combined_colors = obj.data.color_attributes.new(name='QuartzSurface', type='FLOAT_COLOR', domain='CORNER')
    for index, value in enumerate(retained_colors):
        combined_colors.data[index].color = value
    obj.data.color_attributes.active_color = combined_colors
    part = bpy.data.objects.new('QuartzSurface_Working', obj.data.copy())
    bpy.context.collection.objects.link(part)
    filter_faces(part, True)
    filter_faces(obj, False)
    part.data.materials.clear()
    part.data.materials.append(quartz_material)
    for poly in part.data.polygons:
        poly.material_index = 0
        poly.use_smooth = False
    bevel_marker = bpy.data.materials.get('QuartzSurface_BevelMarker') or bpy.data.materials.new('QuartzSurface_BevelMarker')
    part.data.materials.append(bevel_marker)
    activate(part)
    bevel = part.modifiers.new('Quartz_035mm_Edge', 'BEVEL')
    bevel.width = P['bevel_width_cm']
    bevel.segments = P['bevel_segments']
    bevel.limit_method = 'ANGLE'
    bevel.angle_limit = math.radians(P['bevel_angle_degrees'])
    bevel.affect = 'EDGES'
    bevel.material = 1
    bevel.harden_normals = True
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    color = part.data.color_attributes.get('QuartzSurface')
    if color:
        part.data.color_attributes.remove(color)
    color = part.data.color_attributes.new(name='QuartzSurface', type='FLOAT_COLOR', domain='CORNER')
    part.data.color_attributes.active_color = color
    part.data.color_attributes.render_color_index = list(part.data.color_attributes).index(color)
    uv = part.data.uv_layers.active or part.data.uv_layers.new(name='UVMap')
    for poly in part.data.polygons:
        edge = float(poly.material_index == 1)
        angle = math.atan2(poly.normal.y, poly.normal.x)
        variation = .5 + .35 * math.sin(angle * 3.17 + poly.normal.z * 2.4)
        tangent = Vector((-poly.normal.y, poly.normal.x, 0))
        if tangent.length < .05:
            tangent = Vector((1, 0, 0))
            bitangent = Vector((0, 1, 0))
        else:
            tangent.normalize()
            bitangent = Vector((0, 0, 1))
        for index in poly.loop_indices:
            co = part.data.vertices[part.data.loops[index].vertex_index].co
            color.data[index].color = (variation, edge, 0, 1)
            uv.data[index].uv = (co.dot(tangent) / P['texture_u_cm'],
                                 (co.dot(bitangent) - P['root_z_cm']) / P['texture_v_cm'])
        poly.material_index = 0
        poly.use_smooth = bool(edge)
    part.data.materials.pop(index=1)
    # Join only the refined quartz back into the frozen original non-quartz mesh.
    activate(obj)
    part.select_set(True)
    bpy.ops.object.join()
    obj.data.color_attributes.active_color = obj.data.color_attributes['QuartzSurface']
    obj.name = entry['name']
    desired = [quartz_material if m.name.startswith('M_Staff_Quartz') else m for m in retained_materials]
    old_slots = list(obj.data.materials)
    face_materials = [old_slots[p.material_index] for p in obj.data.polygons]
    obj.data.materials.clear()
    for mat in desired:
        obj.data.materials.append(mat)
    for poly, mat in zip(obj.data.polygons, face_materials):
        poly.material_index = next(i for i, candidate in enumerate(desired) if candidate == mat or candidate.name == mat.name)
    obj['quartz_surface_revision'] = 35
    obj['quartz_source'] = entry['fbx']
    obj['author_units'] = 'UE centimetres'
    objects.append(obj)
    export = OUT / (obj.name + '.fbx')
    activate(obj)
    bpy.ops.export_scene.fbx(filepath=str(export), use_selection=True, object_types={'MESH'},
        axis_forward='-Y', axis_up='Z', bake_anim=False, mesh_smooth_type='FACE',
        use_tspace=False, apply_scale_options='FBX_SCALE_ALL', path_mode='AUTO', embed_textures=False,
        colors_type='LINEAR')
    manifest.append({'name': obj.name, 'fbx': str(export), 'slots': entry['slots'],
                     'materials': [m.name for m in obj.data.materials],
                     'triangles': sum(len(p.vertices) - 2 for p in obj.data.polygons)})

# Reuse the existing editable wood/hemp shaders without touching their geometry.
with bpy.data.libraries.load(str(SOURCE), link=False) as (src, dst):
    dst.materials = [n for n in src.materials if n.startswith(('M_Staff_BranchWoodV19', 'M_Staff_HempV19'))]
for material in dst.materials:
    if not material:
        continue
    name = re.sub(r'\.\d{3}$', '', material.name)
    for obj in objects:
        for slot in obj.material_slots:
            if slot.material and re.sub(r'\.\d{3}$', '', slot.material.name) == name:
                slot.material = material

for obj in bpy.context.scene.objects:
    obj.hide_render = obj.name != 'SM_Staff_Base'
    obj.hide_set(obj.name != 'SM_Staff_Base')
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1.0
bpy.context.scene['quartz_surface_stage'] = 'V35 first candidate: surface and transmission; no interior volume'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'Staff_QuartzSurface_V35.blend'))
(OUT / 'meshes.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
(ROOT / 'author-receipt.json').write_text(json.dumps({
    'complete': True, 'meshes': manifest, 'blend': str(ROOT / 'Staff_QuartzSurface_V35.blend'),
    'textures': [normal_image.name, surface_image.name], 'bevel_width_cm': P['bevel_width_cm'],
    'runtime_tested': False, 'rendered': False, 'internal_volume_added': False,
    'source': 'Frozen installed UE meshes, refined locally in Blender'}, indent=2), encoding='utf-8')
print('STAFF_QUARTZ_V35_AUTHORED meshes=2 textures=2 rendered=false', flush=True)
