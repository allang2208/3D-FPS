"""Give the installed broadblade a substantial spine and supported broad faces."""
import json
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector

P = Path(__file__).resolve().parent
V1 = P.parent / 'Broadblade20260922'
NAME = 'SM_Highland_Blade_Broadblade_ThickV2'
ICON = 'ue_highland_claymore_blade_1_highland_broadblade.png'
SOURCE = V1 / 'HighlandClaymore_Broadblade_Editable.blend'
for folder in ['Export', 'Icons']:
    (P / folder).mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
base = bpy.data.objects['SM_Highland_Blade_Broadblade_V1']
obj = base.copy()
obj.data = base.data.copy()
obj.name = NAME
obj.data.name = NAME
scene.collection.objects.link(obj)
obj.hide_set(False)
obj.hide_render = False
mesh = obj.data
source_count = {'vertices': len(mesh.vertices), 'faces': len(mesh.polygons)}

# The outer V1 steel contains long, sparse triangles. Add authoring samples
# before changing the section, preserving all UVs and interpolated corner normals.
normal_attr = mesh.attributes.get('SurfaceNormal') or mesh.attributes.new('SurfaceNormal', 'FLOAT_VECTOR', 'CORNER')
normal_attr.data.foreach_set('vector', np.array([tuple(n.vector) for n in mesh.corner_normals], dtype=np.float32).ravel())
bm = bmesh.new()
bm.from_mesh(mesh)
for cuts in [2, 1]:
    edges = [e for e in bm.edges if e.calc_length() > .010 and all(v.co.z > .105 for v in e.verts)]
    if edges:
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts, use_grid_fill=True, smooth=0.)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
bm.to_mesh(mesh)
bm.free()
mesh.update()
points = np.array([tuple(v.co) for v in mesh.vertices], dtype=np.float64)
normals = np.array([tuple(v.vector) for v in mesh.attributes['SurfaceNormal'].data], dtype=np.float64)
normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-10)

# Native cross-section envelope gives the bevel its own width at every height,
# including the curved shoulders and pointed last quarter of the blade.
mesh.calc_loop_triangles()
tri = np.array([t.vertices[:] for t in mesh.loop_triangles], dtype=np.int32)
edges = np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]])
a, b = points[edges[:, 0]], points[edges[:, 1]]
heights = np.linspace(.09, .879, 220)
left, right = [], []
for z in heights:
    selected = (np.minimum(a[:, 2], b[:, 2]) <= z) & (np.maximum(a[:, 2], b[:, 2]) > z)
    aa, bb = a[selected], b[selected]
    t = (z - aa[:, 2]) / (bb[:, 2] - aa[:, 2])
    x = aa[:, 0] + (bb[:, 0] - aa[:, 0]) * t
    left.append(-float(x.min()))
    right.append(float(x.max()))


def smooth(t):
    t = np.clip(t, 0., 1.)
    return t * t * (3. - 2. * t)


def shape(p):
    q = p.copy()
    x, y, z = p.T
    half_width = np.where(x < 0, np.interp(z, heights, left), np.interp(z, heights, right))
    radial = np.abs(x) / np.maximum(half_width, .002)
    root = smooth((z - .105) / .070)
    point = 1. - smooth((z - .655) / .225)
    # Add 4.2 mm on each face at the spine, retaining original engraved relief.
    # Broad supporting faces carry most of that volume; the last 31% of each
    # half-width forms the ground bevel and fades to the original cutting edge.
    face_support = 1. - .18 * smooth((radial - .15) / .48)
    grind = 1. - smooth((radial - .67) / .31)
    lift = .0042 * root * point * face_support * grind
    q[:, 1] = y + np.tanh(y / .00035) * lift
    return q


eps = 1e-6
jac = np.empty((len(points), 3, 3), dtype=np.float64)
for axis in range(3):
    step = np.zeros(3)
    step[axis] = eps
    jac[:, :, axis] = (shape(points + step) - shape(points - step)) / (2. * eps)
indices = np.array([loop.vertex_index for loop in mesh.loops])
inverse_transpose = np.linalg.inv(jac).transpose(0, 2, 1)
normals = np.einsum('nij,nj->ni', inverse_transpose[indices], normals)
normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-10)
mesh.vertices.foreach_set('co', shape(points).astype(np.float32).ravel())
for face in mesh.polygons:
    face.use_smooth = True
mesh.update()
mesh.normals_split_custom_set(normals.tolist())
mesh.attributes['SurfaceNormal'].data.foreach_set('vector', normals.astype(np.float32).ravel())
obj['design_revision'] = 'ThickV2: substantial spine, broad supported faces, tapered grinding bevel'
obj['maximum_added_total_thickness_mm'] = 8.4

for other in scene.objects:
    if other.type == 'MESH':
        visible = other == obj or other.name in [
            'SM_Highland_Guard_factory', 'SM_Highland_Grip_factory', 'SM_Highland_Pommel_factory']
        other.hide_set(not visible)
        other.hide_render = not visible
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.export_scene.fbx(filepath=str(P / 'Export' / (NAME + '.fbx')),
    use_selection=True, object_types={'MESH'}, axis_forward='-Y', axis_up='Z',
    add_leaf_bones=False, bake_anim=False, mesh_smooth_type='FACE', use_tspace=True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'Highland_Broadblade_ThickV2_Editable.blend'))

# Reuse the exact previous icon studio, camera and lights. Replace only its part.
with bpy.data.libraries.load(str(V1 / 'HighlandClaymore_Broadblade_MenuIcon_Editable.blend'), link=False) as (available, data):
    data.objects = ['Menu camera blade left', 'Key', 'Fill', 'Rim']
    data.worlds = ['Highland broadblade neutral menu studio']
for imported in data.objects:
    scene.collection.objects.link(imported)
scene.camera = next(o for o in data.objects if o.type == 'CAMERA')
scene.world = data.worlds[0]
scene.camera.data.ortho_scale = .875 / .83
for other in scene.objects:
    if other.type == 'MESH':
        other.hide_render = other != obj
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    gpu = [d for d in prefs.devices if d.type == 'OPTIX']
    for device in prefs.devices:
        device.use = device in gpu
    if gpu:
        scene.cycles.device = 'GPU'
except Exception:
    pass
scene.render.resolution_x = scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.render.filepath = str(P / 'Icons' / ICON)
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'Highland_Broadblade_ThickV2_MenuIcon_Editable.blend'))
manifest = {
    'weapon': 'ue_highland_claymore', 'option': 'highland_broadblade',
    'mesh': NAME, 'source_blend': str(SOURCE), 'source_object': base.name,
    'ue_folder': '/Game/Weapons/HighlandClaymore20260922/BroadbladeThicknessV2_20260922',
    'icon': ICON, 'dimensions': 'metres; width X, thickness Y, tip +Z',
    'design': {'added_spine_thickness_mm': 8.4, 'intended_middle_spine_mm': [15, 17],
               'root_fade_cm': [10.5, 17.5], 'tip_fade_cm': [65.5, 88],
               'grinding_bevel_half_width_fraction': [.67, .98],
               'width_length_and_mount': 'Same as V1; only thickness changed'},
    'source_topology': source_count,
    'topology': {'vertices': len(mesh.vertices), 'triangles': len(mesh.polygons),
                 'uv': 'Native UVs interpolated through local subdivision',
                 'normals': 'Original corner normals interpolated and Jacobian transformed'},
    'production_icon': {'size': [1024, 1024], 'direction': 'Blade tip left',
                        'background': 'Transparent', 'studio': 'Unchanged V1 orthographic studio'},
    'gameplay_changes': False, 'tested': False, 'acceptance_rendered': False}
(P / 'authoring.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print('HIGHLAND_BROADBLADE_THICK_V2_AUTHORED ' + str(P / 'authoring.json'), flush=True)
