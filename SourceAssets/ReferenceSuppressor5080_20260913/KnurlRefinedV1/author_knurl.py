"""Local exterior knurl repair on the selected generated source, preserving the body."""
import bpy
import bmesh
import json
import math
import numpy as np
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
SOURCE = ROOT / 'seed_91353' / 'Suppressor_5080_Candidate_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
obj = next(o for o in scene.objects if o.type == 'MESH')
mesh = obj.data
positions = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
mesh.vertices.foreach_get('co', positions)
positions = positions.reshape(-1, 3)
lo, hi = positions.min(axis=0), positions.max(axis=0)
length = float(hi[0] - lo[0])
center = (lo + hi) * 0.5
t = (positions[:, 0] - lo[0]) / length
dy = positions[:, 1] - center[1]
dz = positions[:, 2] - center[2]
radii = np.sqrt(dy * dy + dz * dz)
angles = np.arctan2(dz, dy)

# Read the existing tail silhouette in angular sectors and keep its low-frequency
# cross-section. Repeated pits and lumpy ridges are deliberately excluded.
band = (t > .06) & (t < .29)
sector_centers, sector_radii = [], []
for k in range(96):
    a0 = -math.pi + 2 * math.pi * k / 96
    a1 = -math.pi + 2 * math.pi * (k + 1) / 96
    sample = radii[band & (angles >= a0) & (angles < a1)]
    if len(sample):
        sector_centers.append((a0 + a1) * .5)
        sector_radii.append(float(np.quantile(sample, .85)))
theta = np.array(sector_centers)
design = np.column_stack((np.ones_like(theta), np.cos(theta), np.sin(theta), np.cos(2*theta), np.sin(2*theta)))
coeff = np.linalg.lstsq(design, np.array(sector_radii), rcond=None)[0]
nominal_radius = float(coeff[0])

# Material values come from the imported material's images on the smooth body.
# The body's image nodes and original UVs remain untouched. The rebuilt band has
# its own constant coating material; its diagonal relief is actual geometry.
loop_vertices = np.empty(len(mesh.loops), dtype=np.int32)
mesh.loops.foreach_get('vertex_index', loop_vertices)
uvs = np.empty(len(mesh.loops) * 2, dtype=np.float32)
mesh.uv_layers.active.data.foreach_get('uv', uvs)
uvs = uvs.reshape(-1, 2)
sample_loops = np.flatnonzero((t[loop_vertices] > .4) & (t[loop_vertices] < .8))[::31]
sample_uv = uvs[sample_loops]
source_material = mesh.materials[0]
bsdf = next(n for n in source_material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')

def image_sample(image):
    # Packed image bytes are also retained independently for the local source.
    texture_dir = OUT / 'SourceTextures'
    texture_dir.mkdir(exist_ok=True)
    if image.packed_file:
        target = texture_dir / (image.name + '.png')
        target.write_bytes(bytes(image.packed_file.data))
    w, h = image.size
    pixels = np.asarray(image.pixels[:], dtype=np.float32).reshape(h, w, 4)
    ix = np.clip((sample_uv[:,0] * w).astype(int), 0, w-1)
    iy = np.clip((sample_uv[:,1] * h).astype(int), 0, h-1)
    return np.median(pixels[iy, ix, :3], axis=0)

color_nodes = [n for n in source_material.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image and n.image.colorspace_settings.name == 'sRGB']
data_nodes = [n for n in source_material.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image and n.image.colorspace_settings.name != 'sRGB']
color = image_sample(color_nodes[0].image) if color_nodes else np.array(bsdf.inputs['Base Color'].default_value[:3])
if color_nodes:
    color = np.where(color <= .04045, color / 12.92, ((color + .055) / 1.055) ** 2.4)
mr = image_sample(data_nodes[0].image) if data_nodes else np.array([1., .5, .8])
roughness = float(mr[1])
metallic = float(mr[2])

# Cache source corner normals, then remove only the exterior faces covered by
# the new band. BMesh carries source UV/material layers through this local edit.
old_normals = np.empty(len(mesh.corner_normals) * 3, dtype=np.float32)
mesh.corner_normals.foreach_get('vector', old_normals)
old_normals = old_normals.reshape(-1, 3)
old_loop_starts = [p.loop_start for p in mesh.polygons]
bm = bmesh.new()
bm.from_mesh(mesh)
bm.faces.ensure_lookup_table()
source_face_layer = bm.faces.layers.int.new('knurl_source_face')
for face in bm.faces:
    face[source_face_layer] = face.index

start_t, end_t = .025, .329
delete_start, delete_end = .026, .328
removed = []
for face in bm.faces:
    centroid = face.calc_center_median()
    axial = (centroid.x - lo[0]) / length
    radial = math.hypot(centroid.y - center[1], centroid.z - center[2])
    if delete_start < axial < delete_end and radial > nominal_radius * .81:
        removed.append(face)
removed_face_count = len(removed)
bmesh.ops.delete(bm, geom=removed, context='FACES_ONLY')
isolated = [v for v in bm.verts if not v.link_faces]
if isolated:
    bmesh.ops.delete(bm, geom=isolated, context='VERTS')
bm.faces.index_update()
preserved_normals = []
for face in bm.faces:
    old_start = old_loop_starts[face[source_face_layer]]
    for offset, loop in enumerate(face.loops):
        preserved_normals.append(old_normals[old_start + offset].tolist())
bm.to_mesh(mesh)
bm.free()
mesh.update()
mesh.normals_split_custom_set(preserved_normals)
if 'knurl_source_face' in mesh.attributes:
    mesh.attributes.remove(mesh.attributes['knurl_source_face'])

coating = bpy.data.materials.new('Knurl_Refined_OriginalCoating')
coating.use_nodes = True
coating.node_tree.nodes.clear()
shader = coating.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
output = coating.node_tree.nodes.new('ShaderNodeOutputMaterial')
coating.node_tree.links.new(shader.outputs['BSDF'], output.inputs['Surface'])
shader.inputs['Base Color'].default_value = (*[float(c) for c in color], 1)
shader.inputs['Roughness'].default_value = roughness
shader.inputs['Metallic'].default_value = metallic
coating.diffuse_color = (*[float(c) for c in color], 1)

around, rows, flute_count = 560, 176, 56
start_x, end_x = lo[0] + length * start_t, lo[0] + length * end_t
relief_depth = nominal_radius * .012
tilt = math.radians(34)
twist_per_length = flute_count * math.tan(tilt) / nominal_radius

def smoothstep(x):
    x = min(1., max(0., x))
    return x*x*(3.-2.*x)

vertices, faces = [], []
for j in range(rows + 1):
    u = j / rows
    x = start_x + (end_x-start_x) * u
    fade = smoothstep(u/.035) * smoothstep((1-u)/.035)
    for i in range(around):
        angle = i * 2*math.pi/around
        radius = float(coeff @ np.array([1.,math.cos(angle),math.sin(angle),math.cos(2*angle),math.sin(2*angle)]))
        phase = flute_count * angle + twist_per_length * (x-start_x)
        shallow_groove = ((1 + math.cos(phase)) * .5) ** 2
        radius -= relief_depth * fade * shallow_groove
        vertices.append((float(x),float(center[1]+radius*math.cos(angle)),float(center[2]+radius*math.sin(angle))))
for j in range(rows):
    for i in range(around):
        ni = (i+1) % around
        faces.append((j*around+i,j*around+ni,(j+1)*around+ni,(j+1)*around+i))
new_mesh = bpy.data.meshes.new('TailKnurl_RegularShallowRelief')
new_mesh.from_pydata(vertices, [], faces)
new_mesh.update()
sleeve = bpy.data.objects.new('TailKnurl_LocalRefinement', new_mesh)
scene.collection.objects.link(sleeve)
sleeve.matrix_world = obj.matrix_world.copy()
new_mesh.materials.append(coating)
uv_layer = new_mesh.uv_layers.new(name='Knurl_CylindricalUV')
for poly in new_mesh.polygons:
    j, i = divmod(poly.index, around)
    coords = ((j/rows,i/around),(j/rows,(i+1)/around),((j+1)/rows,(i+1)/around),((j+1)/rows,i/around))
    for loop_index, uv in zip(poly.loop_indices, coords):
        uv_layer.data[loop_index].uv = uv
    poly.use_smooth = True

scene['local_refinement'] = 'Only tail exterior knurl replaced; original main body and end rims retained'
scene['asset_status'] = 'Locally refined candidate; not game tested'
scene['reference_source_blend'] = str(SOURCE)
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
sleeve.select_set(True)
bpy.context.view_layer.objects.active = sleeve
bpy.ops.file.pack_all()
blend_path = OUT / 'Suppressor_KnurlRefinedV1.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
glb_path = OUT / 'Suppressor_KnurlRefinedV1.glb'
bpy.ops.export_scene.gltf(filepath=str(glb_path), export_format='GLB', use_selection=True, export_normals=True, export_materials='EXPORT', export_texcoords=True)
receipt = {
    'source':str(SOURCE),
    'operation':'Local tail exterior reconstruction on original generated source',
    'blend':blend_path.name,
    'glb':glb_path.name,
    'normalized_axial_interval':[start_t,end_t],
    'removed_original_tail_faces':removed_face_count,
    'new_relief_quads':len(faces),
    'circumferential_groove_count':flute_count,
    'groove_tilt_degrees':34,
    'groove_depth_to_radius':.012,
    'coating_linear_base_color':color.tolist(),
    'coating_roughness':roughness,
    'coating_metallic':metallic,
    'coating_source':'Median original smooth-body image values; local constant PBR material, not a new texture set',
    'preserved':'Retained source vertex positions, faces, UVs, material slots and imported corner normals',
    'coordinate_units':'Unscaled generator coordinates, not manufacturing dimensions',
    'game_tested':False,
    'ue_imported':False,
}
(OUT/'author_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('LOCAL_KNURL_REFINEMENT_SAVED',json.dumps(receipt),flush=True)
