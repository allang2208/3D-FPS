"""Keep the dragon root, attach an authored closed Yanling blade and export 3 LODs."""
import bpy, bmesh, json, math
from pathlib import Path
import numpy as np
from mathutils import Vector, Matrix
P = Path(__file__).resolve().parent
ROOT = P.parents[2]
OUT = P / 'Export'
OUT.mkdir(exist_ok=True)
NAME = 'SM_TangDao_Blade_yanling_edge'
UE = '/Game/Weapons/TangDao20261002/YanlingBlade20261002'
CUT = .34
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(P.parent / 'SurfaceV2/TangDao_SurfaceV2_Editable.blend'))
source = bpy.data.objects['SM_TangDao_Blade_factory']
mesh = source.data.copy()
normals = [tuple(n.vector) for n in source.data.corner_normals]
attribute = mesh.attributes.get('YanlingCornerNormal') or mesh.attributes.new('YanlingCornerNormal', 'FLOAT_VECTOR', 'CORNER')
for dst, src in zip(attribute.data, normals):
    dst.vector = src
bm = bmesh.new()
bm.from_mesh(mesh)
nl = bm.loops.layers.float_vector['YanlingCornerNormal']
ul = bm.loops.layers.uv[0]
bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                      dist=1e-7, plane_co=(0, 0, CUT), plane_no=(0, 0, 1), clear_outer=True)
edges = [e for e in bm.edges if e.is_boundary and all(abs(v.co.z - CUT) < .000002 for v in e.verts)]
graph = {}
for e in edges:
    for v in e.verts:
        graph.setdefault(v, []).append(e.other_vert(v))
first = min(graph, key=lambda v: (v.co.x, v.co.y))
ring = []
current, previous = first, None
while current not in ring:
    ring.append(current)
    nxt = next(v for v in graph[current] if v != previous)
    previous, current = current, nxt
area = sum(a.co.x * b.co.y - b.co.x * a.co.y for a, b in zip(ring, ring[1:] + ring[:1]))
if area < 0:
    ring.reverse()
i = min(range(len(ring)), key=lambda i: (ring[i].co.x, ring[i].co.y))
ring = ring[i:] + ring[:i]
root_points = np.array([tuple(v.co) for v in ring])

def fractions(points):
    distances = np.linalg.norm(np.roll(points, -1, axis=0) - points, axis=1)
    return np.r_[0., np.cumsum(distances)] / distances.sum()

root_fraction = fractions(root_points)
profile_z = np.array([.34, .40, .56, .70, .775, .805, .825, .88])
profile_edge = np.array([-.0296, -.0274, -.0176, -.0035, .0095, .024, .057, .1137])
profile_spine = np.array([.0316, .034, .045, .063, .079, .088, .094, .114])
ts = np.unique(np.r_[np.linspace(0, 1, 65), .24, .30, .58, .60, .614, .628, .64, .652, .666, .68,
                     .74, .76, .774, .788, .80, .812, .826, .84, .95, .976])
cross = [(float(t), -1) for t in ts] + [(float(t), 1) for t in ts[::-1]]

def smooth(a, b, q):
    t = np.clip((q - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)

def analytic(z, t, side):
    lo = np.interp(z, profile_z, profile_edge)
    hi = np.interp(z, profile_z, profile_spine)
    # A broad honed bevel, planar steel face and narrow spine chamfer.
    thickness = np.interp(t, [0, .24, .30, .95, .976, 1], [.00010, .00310, .00360, .00385, .00320, .00245])
    thickness *= 1 - .85 * smooth(.805, .88, z)
    grooves = max(math.exp(-((t - .64) / .026) ** 4), math.exp(-((t - .80) / .026) ** 4))
    gate = smooth(.405, .438, z) * (1 - smooth(.745, .785, z))
    thickness -= .00055 * grooves * gate
    return np.array([lo + t * (hi - lo), side * max(thickness, .000075), z])

template = np.array([analytic(.40, t, side) for t, side in cross])
body_fraction = fractions(template)
root_closed = np.vstack([root_points, root_points[0]])

def point(z, index):
    t, side = cross[index]
    target = analytic(z, t, side)
    original = np.array([np.interp(body_fraction[index], root_fraction, root_closed[:, axis]) for axis in range(3)])
    original[2] = z
    blend = smooth(CUT, .40, z)
    return original * (1 - blend) + target * blend

def uv(index, z):
    t, side = cross[index]
    return (.02 + .46 * t if side == -1 else .98 - .46 * t, (z - CUT) / (.88 - CUT))

def body_face(vertices, coords, strip=None, z=None):
    f = bm.faces.new(vertices)
    f.material_index = 1
    f.smooth = True
    f.normal_update()
    for loop, coord in zip(f.loops, coords):
        loop[ul].uv = coord
        loop[nl] = f.normal
    return f

# Bridge the original perimeter to the new body's first perimeter without caps,
# retaining the exact source mounting area and every original dragon/root face.
zs = np.unique(np.r_[.34025, .342, .346, .352, .362, .375, .39, np.linspace(.4, .88, 217), profile_z[1:]])
body_rings = [[bm.verts.new(point(float(z), i)) for i in range(len(cross))] for z in zs]
n, m = len(ring), len(cross)
a = b = 0
new = body_rings[0]
while a < n or b < m:
    ai, bi = a % n, b % m
    if a < n and (b == m or root_fraction[a + 1] < body_fraction[b + 1]):
        f = body_face([ring[ai], ring[(a + 1) % n], new[bi]],
                      [uv(bi, CUT), uv(bi, CUT), uv(bi, zs[0])])
        # Give the short seam triangle a proper perimeter UV, including a
        # distinct U for each root corner.
        for k, loop in enumerate(f.loops):
            if k < 2:
                fraction = root_fraction[(a + k) % n]
                loop[ul].uv.x = np.interp(fraction, body_fraction, np.r_[[uv(i, CUT)[0] for i in range(m)], uv(0, CUT)[0]])
        a += 1
    else:
        body_face([ring[ai], new[(b + 1) % m], new[bi]],
                  [uv(bi, CUT), uv((b + 1) % m, zs[0]), uv(bi, zs[0])])
        b += 1
for j, (lower, upper) in enumerate(zip(body_rings, body_rings[1:])):
    za, zb = float(zs[j]), float(zs[j + 1])
    for i in range(m):
        k = (i + 1) % m
        f = body_face([lower[i], lower[k], upper[k], upper[i]], [uv(i, za), uv(k, za), uv(k, zb), uv(i, zb)])
        # Preserve clean cross-section planes and smoothly flowing longitudinal
        # panels. The angular tip uses its actual planar face normal.
        if za < .805:
            epsilon = .00001
            ci, ck = cross[i], cross[k]
            for loop, zz in zip(f.loops, [za, za, zb, zb]):
                az = .5 * (point(zz + epsilon, i) + point(zz + epsilon, k))
                bz = .5 * (point(zz - epsilon, i) + point(zz - epsilon, k))
                across = point(zz, k) - point(zz, i)
                normal = np.cross(across, az - bz)
                length = np.linalg.norm(normal)
                if length > 1e-12:
                    loop[nl] = Vector(normal / length)
tip_center = bm.verts.new(sum((v.co for v in body_rings[-1]), Vector()) / m)
for i in range(m):
    k = (i + 1) % m
    body_face([body_rings[-1][i], body_rings[-1][k], tip_center], [uv(i, .88), uv(k, .88), (.5, 1.)])
bm.to_mesh(mesh)
bm.free()
mesh.update()
for f in mesh.polygons:
    f.use_smooth = True
mesh.normals_split_custom_set([tuple(v.vector.normalized()) for v in mesh.attributes['YanlingCornerNormal'].data])

# Keep the original material slot name stable; only the distal steel has a new
# UV atlas. Both slots receive native blade-rune materials in Unreal.
steel = bpy.data.materials.new('M_TangDaoYanlingSteel')
steel.use_nodes = True
nt = steel.node_tree
bs = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
for key, socket in [('BaseColor', 'Base Color'), ('Normal', 'Normal'), ('ORM', None)]:
    image = bpy.data.images.load(str(P / 'Textures' / ('TangDao_Yanling_' + key + '.png')), check_existing=True)
    image.colorspace_settings.name = 'sRGB' if key == 'BaseColor' else 'Non-Color'
    node = nt.nodes.new('ShaderNodeTexImage')
    node.image = image
    if key == 'ORM':
        separate = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(node.outputs['Color'], separate.inputs[0])
        nt.links.new(separate.outputs['Green'], bs.inputs['Roughness'])
        nt.links.new(separate.outputs['Blue'], bs.inputs['Metallic'])
    elif key == 'Normal':
        normal = nt.nodes.new('ShaderNodeNormalMap')
        nt.links.new(node.outputs['Color'], normal.inputs['Color'])
        nt.links.new(normal.outputs['Normal'], bs.inputs['Normal'])
    else:
        nt.links.new(node.outputs['Color'], bs.inputs[socket])
mesh.materials.append(steel)
obj = bpy.data.objects.new(NAME, mesh)
bpy.context.scene.collection.objects.link(obj)
obj.matrix_world = Matrix.Identity(4)
for other in bpy.context.scene.objects:
    if other.type == 'MESH':
        other.hide_render = other != obj
        other.hide_set(other != obj)
obj.hide_set(False)
lod_group = bpy.data.objects.new(NAME + '_LODGroup', None)
lod_group['fbx_type'] = 'LodGroup'
bpy.context.scene.collection.objects.link(lod_group)
obj.parent = lod_group
obj.name = NAME + '_LOD0'
lods = [obj]
for level, ratio in [(1, .55), (2, .26)]:
    lod = obj.copy()
    lod.data = obj.data.copy()
    bpy.context.scene.collection.objects.link(lod)
    lod.name = NAME + '_LOD' + str(level)
    lod.hide_set(False)
    bpy.context.view_layer.objects.active = lod
    modifier = lod.modifiers.new('Distance LOD', 'DECIMATE')
    modifier.ratio = ratio
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    lod.hide_render = True
    lods.append(lod)
bpy.ops.object.select_all(action='DESELECT')
lod_group.select_set(True)
for lod in lods:
    lod.hide_set(False)
    lod.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.export_scene.fbx(filepath=str(OUT / (NAME + '.fbx')), use_selection=True,
                         object_types={'MESH', 'EMPTY'}, axis_forward='-Y', axis_up='Z',
                         add_leaf_bones=False, bake_anim=False, mesh_smooth_type='FACE', use_tspace=True)
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT / (NAME + '.glb')), use_selection=True, export_format='GLB')
for lod in lods[1:]:
    lod.hide_set(True)
obj.hide_set(False)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'TangDao_YanlingBlade_Editable.blend'))
counts = []
for lod in lods:
    lod.data.calc_loop_triangles()
    counts.append(len(lod.data.loop_triangles))
manifest = {
    'id': 'yanling_edge', 'weapon': 'ue_tang_dao', 'slot': 'blade_1', 'name': '破锋燕翎刀身',
    'ue_root': UE, 'mesh_name': NAME, 'mesh': UE + '/Meshes/' + NAME + '.' + NAME,
    'interface': 'tang_dao_hilt_v1', 'location_cm': [0, 0, 0],
    # Retain the common attack sample contract; the authored visible tip keeps
    # the same 88 cm longitudinal extent as the original blade.
    'trace_base_cm': [0, 0, 3],
    'trace_tip_cm': [11.389727890491486, -.012784003047272563, 87.99999952316284],
    'rune_dimensions_cm': [14, 12, 74],
    'materials': {
        'M_TangDaoSurface': '/Game/Weapons/TangDao20261002/SurfaceV2/Materials/M_TangDaoBladeRuneSurface.M_TangDaoBladeRuneSurface',
        'M_TangDaoYanlingSteel': UE + '/Materials/M_TangDaoBladeRuneSurface_Yanling.M_TangDaoBladeRuneSurface_Yanling'
    },
    'lod_triangles': counts, 'root_retained_to_cm': CUT * 100,
    'fuller_depth_mm': .55, 'fuller_centers_across_blade': [.64, .80],
    'fuller_z_cm': [40.5, 78.5], 'blade_tip_cm': [11.4, 0, 88],
    'reference': str(P / 'Reference/YanlingBlade_UserReference.png'),
    'reference_original': 'C:/Users/allan/AppData/Local/Temp/codex-clipboard-11a3ba82-08a8-4cb5-83e6-c02cbfb5a94a.png',
    'scope': 'Blade geometry and steel PBR; existing dragon, guard, grip, pommel and mounting retained. Combat recipe: catalog_extension.py',
    'runtime_tested': False
}
(P / 'blade_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('YANLING_BLADE_AUTHORED ' + json.dumps({'lod_triangles': counts, 'mesh': manifest['mesh']}), flush=True)
