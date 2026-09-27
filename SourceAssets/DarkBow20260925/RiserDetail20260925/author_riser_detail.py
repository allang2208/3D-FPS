# Author a closer-range riser: bevel + one subdiv + limb smooth + weighted normals.
# Source is the live ArmsV2 split (Fab bow minus 124 baked-string triangles).
# Units in this file are metres; UE FBX import of the arrow already maps that to cm.
import json
import math
from pathlib import Path
import bpy
import bmesh

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / 'ArmsV2' / 'bow_surface.json'
EXPORT = HERE / 'Export'
EXPORT.mkdir(exist_ok=True)
RECEIPT = HERE / 'authoring.json'

STRING = dict(xmin=-21.79, xmax=-21.13, ymin=-1.26, ymax=-0.61, zmin=-64.05, zmax=64.12)
BEVEL_WIDTH_M = 0.0016
BEVEL_ANGLE = math.radians(32.0)
SMOOTH_FACTOR = 0.32
SMOOTH_ITERS = 5


def hard_stats(mesh):
    angles = []
    hard = 0
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.normal_update()
    for v in bm.verts:
        ns = [f.normal.copy() for f in v.link_faces]
        mx = 0.0
        for i in range(len(ns)):
            for j in range(i + 1, len(ns)):
                d = max(-1.0, min(1.0, ns[i].dot(ns[j])))
                mx = max(mx, math.degrees(math.acos(d)))
        angles.append(mx)
        if mx > 25.0:
            hard += 1
    bm.free()
    angles.sort()
    if not angles:
        return {'hard_verts_25': 0, 'p50': 0, 'p90': 0, 'max': 0}
    return {
        'hard_verts_25': hard,
        'verts': len(angles),
        'p50': round(angles[len(angles) // 2], 2),
        'p90': round(angles[int((len(angles) - 1) * 0.9)], 2),
        'max': round(angles[-1], 2),
    }


def bbox_cm(obj):
    xs, ys, zs = zip(*[obj.matrix_world @ v.co for v in obj.data.vertices])
    return {
        'x': [round(min(xs) * 100, 3), round(max(xs) * 100, 3)],
        'y': [round(min(ys) * 100, 3), round(max(ys) * 100, 3)],
        'z': [round(min(zs) * 100, 3), round(max(zs) * 100, 3)],
        'size': [
            round((max(xs) - min(xs)) * 100, 3),
            round((max(ys) - min(ys)) * 100, 3),
            round((max(zs) - min(zs)) * 100, 3),
        ],
    }


def apply(obj, name):
    bpy.ops.object.modifier_apply(modifier=name)


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
source = json.loads(SRC.read_text(encoding='utf-8'))
keep = []
removed = 0
for i, face in enumerate(source['triangles']):
    pts = [source['positions'][v] for v in face]
    if all(
        STRING['xmin'] <= v[0] <= STRING['xmax']
        and STRING['ymin'] <= v[1] <= STRING['ymax']
        and STRING['zmin'] <= v[2] <= STRING['zmax']
        for v in pts
    ):
        removed += 1
        continue
    keep.append(i)
if removed != 124:
    raise RuntimeError('string island changed: %s' % removed)

used = []
remap = {}
for i in keep:
    for v in source['triangles'][i]:
        if v not in remap:
            remap[v] = len(used)
            used.append(v)
verts = [tuple(c / 100.0 for c in source['positions'][v]) for v in used]
faces = [tuple(remap[v] for v in source['triangles'][i]) for i in keep]
mesh = bpy.data.meshes.new('RiserDetail')
mesh.from_pydata(verts, [], faces)
mesh.update()
for name in ('Body', 'Limb', 'Inlay'):
    mat = bpy.data.materials.new(name)
    mesh.materials.append(mat)
uv = mesh.uv_layers.new(name='UVMap')
loop = 0
for pi, src in enumerate(keep):
    poly = mesh.polygons[pi]
    poly.material_index = int(source['materials'][src])
    poly.use_smooth = True
    for corner in source['uv'][src]:
        uv.data[loop].uv = corner
        loop += 1
obj = bpy.data.objects.new('SM_DarkBow_RiserDetail', mesh)
bpy.context.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)

before = {
    'tris': len(mesh.polygons),
    'verts': len(mesh.vertices),
    'hard': hard_stats(mesh),
    'bbox_cm': bbox_cm(obj),
}

bm = bmesh.new()
bm.from_mesh(mesh)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=5e-5)
bmesh.ops.dissolve_degenerate(bm, dist=5e-5, edges=bm.edges)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(mesh)
bm.free()
mesh.update()

# Shade smooth before any custom normals.
bpy.ops.object.shade_smooth()

bevel = obj.modifiers.new('EdgeBevel', 'BEVEL')
bevel.affect = 'EDGES'
bevel.limit_method = 'ANGLE'
bevel.angle_limit = BEVEL_ANGLE
bevel.width = BEVEL_WIDTH_M
bevel.segments = 3
bevel.use_clamp_overlap = True
try:
    bevel.miter_outer = 'MITER_ARC'
except Exception:
    pass
apply(obj, 'EdgeBevel')

sub = obj.modifiers.new('LimbSubdiv', 'SUBSURF')
sub.subdivision_type = 'CATMULL_CLARK'
sub.levels = 1
sub.render_levels = 1
try:
    sub.use_limit_surface = True
except Exception:
    pass
apply(obj, 'LimbSubdiv')

# Keep grip and nock hooks from melting; only soften the long limbs.
group = obj.vertex_groups.new(name='limbs')
for v in obj.data.vertices:
    z_cm = abs(v.co.z) * 100.0
    if 9.0 <= z_cm <= 61.0:
        group.add([v.index], 1.0, 'REPLACE')
    elif 7.0 <= z_cm < 9.0 or 61.0 < z_cm <= 64.0:
        group.add([v.index], 0.4, 'REPLACE')
sm = obj.modifiers.new('LimbSmooth', 'SMOOTH')
sm.factor = SMOOTH_FACTOR
sm.iterations = SMOOTH_ITERS
sm.vertex_group = 'limbs'
apply(obj, 'LimbSmooth')

# Recalc after bevel/subdiv so leftover 180 deg flips do not stay in the game mesh.
bm = bmesh.new()
bm.from_mesh(obj.data)
bmesh.ops.dissolve_degenerate(bm, dist=5e-5, edges=bm.edges)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(obj.data)
bm.free()
obj.data.update()
if len(obj.data.polygons) > 36000:
    dec = obj.modifiers.new('Density', 'DECIMATE')
    dec.decimate_type = 'COLLAPSE'
    dec.ratio = 36000.0 / float(len(obj.data.polygons))
    dec.use_collapse_triangulate = True
    apply(obj, 'Density')
wn = obj.modifiers.new('WeightedN', 'WEIGHTED_NORMAL')
wn.mode = 'FACE_AREA'
wn.weight = 50
wn.thresh = 0.01
wn.keep_sharp = False
try:
    wn.use_face_influence = True
except Exception:
    pass
apply(obj, 'WeightedN')

# Restore a little thickness if Catmull-Clark pinched the 3.5 cm limb.
size = bbox_cm(obj)
y0 = before['bbox_cm']['size'][1]
y1 = size['size'][1]
if y1 < y0 * 0.92:
    inflate = ((y0 * 0.96) - y1) / 200.0
    disp = obj.modifiers.new('RestoreThick', 'DISPLACE')
    disp.strength = max(0.0002, min(0.0012, inflate))
    disp.mid_level = 0.0
    try:
        disp.direction = 'NORMAL'
    except Exception:
        pass
    apply(obj, 'RestoreThick')

bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
after = {
    'tris': len(obj.data.polygons),
    'verts': len(obj.data.vertices),
    'hard': hard_stats(obj.data),
    'bbox_cm': bbox_cm(obj),
}
if after['tris'] < before['tris']:
    raise RuntimeError('detail pass lost faces')
if after['tris'] > 90000:
    raise RuntimeError('too dense: %s' % after['tris'])
if after['bbox_cm']['size'][2] < 136 or after['bbox_cm']['size'][2] > 146:
    raise RuntimeError('length drifted: %s' % after['bbox_cm']['size'][2])
if after['bbox_cm']['size'][1] < 3.0:
    raise RuntimeError('too thin: %s' % after['bbox_cm']['size'][1])
before_ratio = before['hard']['hard_verts_25'] / max(1, before['hard']['verts'])
after_ratio = after['hard']['hard_verts_25'] / max(1, after['hard']['verts'])
if after['hard']['p50'] > before['hard']['p50'] * 0.55 or after_ratio > before_ratio * 0.7:
    raise RuntimeError('hard edges not reduced: %s -> %s' % (before['hard'], after['hard']))

bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'RiserDetail_Editable.blend'))
bpy.ops.export_scene.fbx(
    filepath=str(EXPORT / 'SM_DarkBow_RiserDetail.fbx'),
    use_selection=True,
    object_types={'MESH'},
    axis_forward='-Y',
    axis_up='Z',
    bake_anim=False,
    mesh_smooth_type='FACE',
    use_tspace=True,
    apply_scale_options='FBX_SCALE_ALL',
)
receipt = {
    'removed_string_tris': removed,
    'before': before,
    'after': after,
    'bevel_width_mm': BEVEL_WIDTH_M * 1000,
    'bevel_angle_deg': 32,
    'subdiv': 1,
    'smooth': {'factor': SMOOTH_FACTOR, 'iterations': SMOOTH_ITERS},
    'fbx': str(EXPORT / 'SM_DarkBow_RiserDetail.fbx'),
    'runtime_tested': False,
}
RECEIPT.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('BOW_RISER_DETAIL_AUTHORED', after['tris'], after['hard'], flush=True)
