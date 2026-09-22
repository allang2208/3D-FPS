"""Author the exclusive Highland broad blade and its production menu icon.

Starts from the installed factory part. Keeps native UVs, rune lane, mounting
rim and tip; moves outer steel to a broad shoulder and tapered heavy profile.
"""
import json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Vector

P = Path(__file__).resolve().parent
SOURCE = P.parent / 'Integration/HighlandClaymore_Modular_Editable.blend'
NAME = 'SM_Highland_Blade_Broadblade_V1'
OPTION = 'highland_broadblade'
ICON = 'ue_highland_claymore_blade_1_' + OPTION
P.joinpath('Export').mkdir(exist_ok=True)
P.joinpath('Icons').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
factory = bpy.data.objects['SM_Highland_Blade_factory']
obj = factory.copy()
obj.data = factory.data.copy()
obj.name = NAME
obj.data.name = NAME
scene.collection.objects.link(obj)
obj.location = Vector()
obj.hide_set(False)
obj.hide_render = False
mesh = obj.data
points = np.array([tuple(v.co) for v in mesh.vertices], dtype=np.float64)
normals = np.array([tuple(n.vector) for n in mesh.corner_normals], dtype=np.float64)


def smooth(t):
    t = np.clip(t, 0., 1.)
    return t * t * (3. - 2. * t)


# Reconstruct the native blade's cross-section envelope for authoring. Separate
# left/right fits retain the generated blade's small asymmetric steel details.
mesh.calc_loop_triangles()
triangles = np.array([t.vertices[:] for t in mesh.loop_triangles], dtype=np.int32)
edges = np.concatenate([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]])
a, b = points[edges[:, 0]], points[edges[:, 1]]
stations = np.linspace(.10, .685, 118)
left, right = [], []
for z in stations:
    active = (np.minimum(a[:, 2], b[:, 2]) <= z) & (np.maximum(a[:, 2], b[:, 2]) > z)
    aa, bb = a[active], b[active]
    t = (z - aa[:, 2]) / (bb[:, 2] - aa[:, 2])
    x = aa[:, 0] + (bb[:, 0] - aa[:, 0]) * t
    left.append(-float(x.min()))
    right.append(float(x.max()))
left_fit = np.polynomial.Polynomial.fit(stations, left, 5)
right_fit = np.polynomial.Polynomial.fit(stations, right, 5)


def deform(p):
    q = p.copy()
    x, y, z = p.T
    # Native hilt contact and engraved root remain exact through 10.5 cm.
    shoulder = smooth((z - .105) / .095)
    tip = 1. - smooth((z - .655) / (.880 - .655))
    envelope_z = np.minimum(z, .655)
    original_half = np.where(x < 0, left_fit(envelope_z), right_fit(envelope_z))
    # Broad, almost parallel middle: 11.0 cm, tapering to 10.6 cm.
    target_half = .055 - .002 * smooth((z - .24) / .415)
    expansion = np.maximum(target_half - original_half, 0.) * shoulder * tip
    # The central 24 mm keeps its native width; only outer steel expands.
    outer = smooth((np.abs(x) - .012) / np.maximum(original_half - .012, .004))
    q[:, 0] = x + np.sign(x) * expansion * outer
    # A 25% thicker central spine falls smoothly to the original cutting edge.
    edge_fraction = np.clip(np.abs(x) / np.maximum(original_half, .014), 0., 1.)
    spine = 1. - smooth((edge_fraction - .30) / .70)
    q[:, 1] = y * (1. + .25 * shoulder * tip * spine)
    return q


# Inverse-transpose Jacobian preserves the authored split surface normals.
eps = 1e-6
jac = np.empty((len(points), 3, 3), dtype=np.float64)
for axis in range(3):
    delta = np.zeros(3)
    delta[axis] = eps
    jac[:, :, axis] = (deform(points + delta) - deform(points - delta)) / (2. * eps)
inverse_transpose = np.linalg.inv(jac).transpose(0, 2, 1)
indices = np.array([loop.vertex_index for loop in mesh.loops])
normals = np.einsum('nij,nj->ni', inverse_transpose[indices], normals)
normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-10)
mesh.vertices.foreach_set('co', deform(points).astype(np.float32).ravel())
for face in mesh.polygons:
    face.use_smooth = True
mesh.update()
mesh.normals_split_custom_set(normals.tolist())
if 'SurfaceNormal' in mesh.attributes:
    mesh.attributes['SurfaceNormal'].data.foreach_set('vector', normals.astype(np.float32).ravel())

for other in scene.objects:
    if other.type == 'MESH':
        show = other == obj or other.name in [
            'SM_Highland_Guard_factory', 'SM_Highland_Grip_factory', 'SM_Highland_Pommel_factory']
        other.hide_set(not show)
        other.hide_render = not show
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.export_scene.fbx(
    filepath=str(P / 'Export' / (NAME + '.fbx')), use_selection=True,
    object_types={'MESH'}, axis_forward='-Y', axis_up='Z',
    add_leaf_bones=False, bake_anim=False, mesh_smooth_type='FACE', use_tspace=True)
obj['option_id'] = OPTION
obj['weapon'] = 'ue_highland_claymore'
obj['design'] = 'Broad shoulders, thick spine, native central runes and unchanged mount'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'HighlandClaymore_Broadblade_Editable.blend'))

# Production UI asset: same actual part, neutral studio, left-facing blade.
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
    devices = [d for d in prefs.devices if d.type == 'OPTIX']
    for device in prefs.devices:
        device.use = device in devices
    if devices:
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
scene.world = bpy.data.worlds.new('Highland broadblade neutral menu studio')
scene.world.use_nodes = True
bg = next(n for n in scene.world.node_tree.nodes if n.type == 'BACKGROUND')
bg.inputs['Color'].default_value = (.2, .2, .2, 1.)
bg.inputs['Strength'].default_value = .65
camera = bpy.data.objects.new('Menu camera blade left', bpy.data.cameras.new('Menu camera blade left'))
scene.collection.objects.link(camera)
scene.camera = camera
camera.data.type = 'ORTHO'
camera.data.clip_start = .001
camera.rotation_euler = Matrix(((0, 1, 0), (0, 0, -1), (-1, 0, 0))).to_euler()
bpy.context.view_layer.update()
corners = [Vector(v) for v in obj.bound_box]
center = sum(corners, Vector()) / 8.
size = max(max(p.x for p in corners) - min(p.x for p in corners),
           max(p.z for p in corners) - min(p.z for p in corners))
camera.location = center + Vector((0, -1.5, 0))
camera.data.ortho_scale = size / .83
for name, offset, energy, diameter in [
    ('Key', (.38, -.60, .35), 95, .75),
    ('Fill', (-.32, -.42, -.15), 45, .65),
    ('Rim', (.12, .28, .30), 65, .5)]:
    lamp = bpy.data.objects.new(name, bpy.data.lights.new(name, 'AREA'))
    scene.collection.objects.link(lamp)
    lamp.data.energy = energy
    lamp.data.shape = 'DISK'
    lamp.data.size = diameter
    lamp.location = center + Vector(offset)
    lamp.rotation_euler = (center - lamp.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = str(P / 'Icons' / (ICON + '.png'))
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'HighlandClaymore_Broadblade_MenuIcon_Editable.blend'))

manifest = {
    'weapon': 'ue_highland_claymore', 'option': OPTION, 'name': '阔锋重刃',
    'mesh': NAME, 'source_blend': str(SOURCE), 'source_object': factory.name,
    'ue_folder': '/Game/Weapons/HighlandClaymore20260922/Broadblade20260922',
    'icon': ICON + '.png', 'units': 'meters; tip +Z, width X, thickness Y',
    'design': {'middle_width_cm': [11.0, 10.6], 'central_lane_width_cm': 2.4,
               'unchanged_root_to_cm': 10.5, 'shoulder_transition_cm': 9.5,
               'tip_taper_start_cm': 65.5, 'blade_tip_cm': 88,
               'central_spine_thickness_mult': 1.25},
    'topology': {'vertices': len(mesh.vertices), 'triangles': len(mesh.loop_triangles),
                 'uv': 'Original factory UV retained', 'normals': 'Jacobian inverse transpose'},
    'icon_settings': {'resolution': [1024, 1024], 'format': 'RGBA transparent PNG',
                      'orientation': 'Tip left; front -Y; orthographic; no mirroring',
                      'subject': NAME, 'production_only': True,
                      'material_note': 'Native PBR; UE time-varying glow not reproduced in still icon'},
    'tested': False, 'acceptance_rendered': False}
(P / 'authoring.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print('HIGHLAND_BROADBLADE_AUTHORED ' + str(P / 'authoring.json'), flush=True)
