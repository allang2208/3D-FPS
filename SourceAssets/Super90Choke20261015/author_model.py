"""Author the reference-led exterior game mesh; no engine edits or rendering.

Coordinates are Blender metres, +X forward, +Z up. The origin is the
attachment's rear visual seating plane, on the circular opening's axis.
The visible front opening terminates in a shallow dark cosmetic recess.
"""
import bpy
import bmesh
import json
import math
import shutil
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parent
EXPORTS = ROOT / 'Exports'
REFERENCE = ROOT / 'Reference'
EXPORTS.mkdir(exist_ok=True)
REFERENCE.mkdir(exist_ok=True)
SOURCE_IMAGE = Path(r'C:/Users/allan/AppData/Local/Temp/codex-clipboard-e8879289-f109-471e-a48c-c070740593cc.png')
shutil.copy2(SOURCE_IMAGE, REFERENCE / 'user_shape_reference.png')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
scene.view_settings.view_transform = 'AgX'

PARAMS = {
    'body_start': .013,
    'body_end': .248,
    'half_width': .023,
    'half_height': .032,
    'vertical_center': -.012,
    'top_corner_radius': .010,
    'bottom_corner_radius': .004,
    'front_recess_radius': .0107,
    'front_recess_depth': .006,
    'body_seams': [.069, .122, .175, .238],
    'seam_depth': .00013,
    'seam_half_width': .00028,
}

MATERIAL_RECIPES = [
    ('Choke_GraphiteShell', (.034, .037, .043, 1), .35, 1.0),
    ('Choke_EndPlate', (.029, .032, .037, 1), .32, 1.0),
    ('Choke_SeamAndRecess', (.006, .007, .009, 1), .64, .15),
    ('Choke_RearSeat', (.034, .035, .037, 1), .42, 1.0),
    ('Choke_RimMetal', (.070, .077, .088, 1), .29, 1.0),
]
MATERIALS = []
for name, color, roughness, metallic in MATERIAL_RECIPES:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = color
    material.roughness = roughness
    material.metallic = metallic
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = color
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    # The shape and bevels supply the normal: no placeholder normal textures.
    MATERIALS.append(material)


def collection(name):
    result = bpy.data.collections.new(name)
    scene.collection.children.link(result)
    return result


def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]


def profile_distance(y, z, inset=0.0):
    z -= PARAMS['vertical_center']
    radius = (PARAMS['top_corner_radius'] if z >= 0 else PARAMS['bottom_corner_radius']) - inset
    radius = max(radius, .0005)
    qy = abs(y) - (PARAMS['half_width'] - inset - radius)
    qz = abs(z) - (PARAMS['half_height'] - inset - radius)
    return math.hypot(max(qy, 0), max(qz, 0)) + min(max(qy, qz), 0) - radius


def perimeter(count, inset=0.0):
    """Sample a continuous rounded rectangular outline around the visual axis."""
    result = []
    for i in range(count):
        angle = 2 * math.pi * i / count
        cy, sz = math.cos(angle), math.sin(angle)
        lo, hi = 0.0, .1
        for _ in range(35):
            radius = (lo + hi) / 2
            if profile_distance(radius * cy, radius * sz, inset) > 0:
                hi = radius
            else:
                lo = radius
        radius = (lo + hi) / 2
        result.append((radius * cy, radius * sz))
    return result


class Loft:
    def __init__(self, count):
        self.count = count
        self.vertices, self.faces, self.materials = [], [], []

    def ring(self, x, shape):
        start = len(self.vertices)
        self.vertices.extend((x, y, z) for y, z in shape)
        return list(range(start, start + len(shape)))

    def circle(self, x, radius, y=0.0, z=0.0):
        return self.ring(x, [(y + radius * math.cos(i * math.tau / self.count),
                             z + radius * math.sin(i * math.tau / self.count))
                            for i in range(self.count)])

    def bridge(self, a, b, material=0):
        for i in range(self.count):
            j = (i + 1) % self.count
            self.faces.append((a[i], a[j], b[j], b[i]))
            self.materials.append(material)

    def cap(self, ring, material=0):
        self.faces.append(tuple(reversed(ring)))
        self.materials.append(material)

    def object(self, name, target):
        mesh = bpy.data.meshes.new(name + '_Mesh')
        mesh.from_pydata(self.vertices, [], self.faces)
        for material in MATERIALS:
            mesh.materials.append(material)
        for polygon, material in zip(mesh.polygons, self.materials):
            polygon.material_index = material
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        for polygon in mesh.polygons:
            polygon.use_smooth = True
        mesh.set_sharp_from_angle(angle=math.radians(42))
        obj = bpy.data.objects.new(name, mesh)
        target.objects.link(obj)
        select([obj])
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.018)
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh.uv_layers.active.name = 'UV0'
        normals = obj.modifiers.new('Planar_Surface_Normals', 'WEIGHTED_NORMAL')
        normals.keep_sharp = True
        normals.weight = 50
        return obj


def make_shell(count, target):
    loft = Loft(count)
    # Closely spaced front and rear rings form the edge highlights in geometry.
    rows = [(PARAMS['body_start'], .0010, 0),
            (PARAMS['body_start'] + .0003, .00045, 0),
            (PARAMS['body_start'] + .0010, 0.0, 0)]
    for center in PARAMS['body_seams']:
        half = PARAMS['seam_half_width']
        depth = PARAMS['seam_depth']
        rows.extend([(center - half, 0, 0),
                     (center - half * .4, depth, 0),
                     (center + half * .4, depth, 2),
                     (center + half, 0, 0)])
    front = PARAMS['body_end']
    rows.extend([(front - .0011, 0, 1),
                 (front - .00055, .00016, 1),
                 (front - .00015, .00050, 1),
                 (front, .0011, 1)])
    rings = []
    for x, inset, material in rows:
        ring = loft.ring(x, perimeter(count, inset))
        if rings:
            loft.bridge(rings[-1], ring, material)
        rings.append(ring)
    loft.cap(rings[0], 3)
    # Front plate, highlight rim, then a shallow visual pocket with a dark cap.
    opening = loft.circle(front, PARAMS['front_recess_radius'] + .0006)
    loft.bridge(rings[-1], opening, 1)
    rim = loft.circle(front - .00065, PARAMS['front_recess_radius'])
    loft.bridge(opening, rim, 4)
    pocket = loft.circle(front - PARAMS['front_recess_depth'], PARAMS['front_recess_radius'])
    loft.bridge(rim, pocket, 2)
    loft.cap(pocket, 2)
    obj = loft.object('Choke_BoxShell', target)
    obj['part_role'] = 'shared_exterior_body'
    return obj


def make_rear_seat(count, target):
    loft = Loft(count)
    previous = None
    # A closed visual seat; adapters remain independent from the shared body.
    for x, radius, material in [(-.0020, .0113, 3), (-.0012, .0120, 3),
                               (.0030, .0120, 3), (.0037, .0131, 3),
                               (.0080, .0131, 3), (.0083, .0129, 2),
                               (.0088, .0129, 2), (.0091, .0131, 3),
                               (.0140, .0131, 3)]:
        ring = loft.circle(x, radius)
        if previous is None:
            loft.cap(ring, 3)
        else:
            loft.bridge(previous, ring, material)
        previous = ring
    loft.cap(previous, 3)
    obj = loft.object('Choke_RearVisualSeat', target)
    obj['part_role'] = 'replaceable_game_mount'
    return obj


def make_front_fastener(count, target, y):
    loft = Loft(count)
    z = -.034
    x = PARAMS['body_end'] + .00002
    rear = loft.circle(x, .0017, y, z)
    edge = loft.circle(x + .00016, .0015, y, z)
    inner = loft.circle(x + .00016, .00055, y, z)
    recess = loft.circle(x + .00003, .00055, y, z)
    loft.cap(rear, 1)
    loft.bridge(rear, edge, 1)
    loft.bridge(edge, inner, 1)
    loft.bridge(inner, recess, 2)
    loft.cap(recess, 2)
    return loft.object('Choke_FrontPin_L' if y < 0 else 'Choke_FrontPin_R', target)


def author_parts(count, target):
    return [make_shell(count, target), make_rear_seat(count, target),
            make_front_fastener(max(12, count // 3), target, -.015),
            make_front_fastener(max(12, count // 3), target, .015)]


def export_mesh(parts, level):
    # Keep editable source pieces separate. Collapse evaluated copies for export.
    select(parts)
    bpy.ops.object.duplicate()
    copies = list(bpy.context.selected_objects)
    for obj in copies:
        select([obj])
        bpy.ops.object.convert(target='MESH')
    select(copies)
    bpy.ops.object.join()
    combined = bpy.context.object
    combined.name = 'SM_ShotgunChoke_Box01_' + level
    triangle_modifier = combined.modifiers.new('Export_Triangles', 'TRIANGULATE')
    triangle_modifier.quad_method = 'FIXED'
    bpy.ops.object.modifier_apply(modifier=triangle_modifier.name)
    combined.data.calc_loop_triangles()
    stats = {'vertices': len(combined.data.vertices),
             'triangles': len(combined.data.loop_triangles)}
    fbx = EXPORTS / (combined.name + '.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True,
                            object_types={'MESH'}, axis_forward='-Y', axis_up='Z',
                            bake_anim=False, add_leaf_bones=False,
                            mesh_smooth_type='FACE', use_tspace=True)
    glb = EXPORTS / (combined.name + '.glb')
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB',
                             use_selection=True, export_materials='EXPORT',
                             export_extras=True, export_animations=False,
                             export_tangents=True)
    stats.update({'fbx': str(fbx), 'glb': str(glb)})
    bpy.data.objects.remove(combined, do_unlink=True)
    return stats


model_collection = collection('01_Editable_Exterior')
parts = author_parts(96, model_collection)
for obj in parts:
    obj['asset_family'] = 'Universal_Shotgun_Choke'
    obj['revision'] = 'Box01_20261015'

lods = {'LOD0': export_mesh(parts, 'LOD0')}
for level, count in [('LOD1', 48), ('LOD2', 24)]:
    lod_collection = collection('Source_' + level)
    lod_parts = author_parts(count, lod_collection)
    lods[level] = export_mesh(lod_parts, level)
    for obj in lod_parts:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(lod_collection)

helpers = collection('02_Assembly_Markers')
for name, x in [('Mount_Origin', 0), ('Visual_Front', PARAMS['body_end'])]:
    marker = bpy.data.objects.new(name, None)
    marker.empty_display_type = 'ARROWS'
    marker.empty_display_size = .025
    marker.location = (x, 0, 0)
    helpers.objects.link(marker)
    marker.hide_render = True
helpers.hide_viewport = True

# Read the source socket transform for the later game attachment stage only.
# The original weapon, skeleton and animation files are never rewritten.
host_source = ROOT.parent / 'Super90WS1Surface20261007/Super90_WS1_Editable.blend'
with bpy.data.libraries.load(str(host_source), link=False) as (source, destination):
    destination.objects = [name for name in source.objects if name == 'SK_Super90']
host_rig = destination.objects[0]
socket = host_rig.data.bones['WPN_SOCKET_Muzzle']
socket_matrix = host_rig.matrix_world @ socket.matrix_local
host_hint = {
    'source': str(host_source),
    'socket': socket.name,
    'native_blender_matrix': [list(row) for row in socket_matrix],
    'native_barrel_forward': [0, 1, 0],
    'canonical_forward': [1, 0, 0],
    'note': 'Source socket metadata only. Runtime fit has not been installed or tested.',
}
bpy.data.objects.remove(host_rig, do_unlink=True)

notes = bpy.data.texts.new('ABOUT_收束器外观模型')
notes.write('''通用霰弹枪收束器 / 方形外壳方案 01
根据用户参考图制作。只制作游戏可见外观，背面细节为美术推断。
主体、后端座、两颗前端饰钉分别可编辑。平面使用加权法线，圆角由几何形成。
UV0 与五组 PBR 材质已建立；未使用噪声凹凸或默认法线贴图。
原点位于后端安装基准，+X 朝前，+Z 朝上。后端连接座可独立调整。
Exports 中为统一原点的 FBX / GLB，分别提供 LOD0 / LOD1 / LOD2。
本轮仅建模和导出，尚未导入 UE、接入枪匠或进行游戏测试。
''')
select(parts)
for workspace in bpy.data.workspaces:
    for screen in [workspace.screens[0]] if workspace.screens else []:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.clip_start = .001
                area.spaces.active.shading.type = 'MATERIAL'
                region = area.spaces.active.region_3d
                region.view_distance = .45
                region.view_location = (.125, 0, -.012)
                direction = Vector((.75, -1.4, .65)).normalized()
                region.view_rotation = direction.to_track_quat('Z', 'Y')

source_file = ROOT / 'ShotgunChoke_Box01_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(source_file))
report = {
    'status': 'model_and_exports_saved',
    'reference': str(REFERENCE / 'user_shape_reference.png'),
    'editable_source': str(source_file),
    'parameters_in_blender_metres': PARAMS,
    'materials': [{'name': name, 'base_color_linear': color, 'roughness': rough, 'metallic': metal}
                  for name, color, rough, metal in MATERIAL_RECIPES],
    'normal_texture': None,
    'lods': lods,
    'super90_source_socket': host_hint,
    'engine_imported': False,
    'gunsmith_integrated': False,
    'rendered': False,
    'runtime_tested': False,
}
(ROOT / 'authoring_receipt.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print('CHOKE_MODEL_SAVED', json.dumps(lods), flush=True)
