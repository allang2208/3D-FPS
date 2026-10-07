"""Azure Dragon claw V10.2: the library Fab Dragon Claw (CaptainHC) driven by the V10.1 gesture.
(V10.6 welded/capped the mesh; V10.9 replaces the flat palm cap with a sculpted palm.)

Geometry, UV atlas and the author's normal atlas are retained (AzureDragonClaw.blend from
author_model.py). Five digits are placed from the nail landmarks exactly as in V9; the skin
recipe is V9's. New for V10.2:
  - four unweighted talon-tip leaves digit_01..04_tip (pinky..index) for the C++ claw trails;
  - the V10.1 lead / swipe / recovery gesture (frames 0/12/24/36, snap at contact frame 18);
  - material data: vertex color (R along digit or talon, G talon, B forearm fade, A 1),
    UV0 = Fab atlas (kept), UV1 = rest XY, UV2 = (rest Z, joint ring), UV3 = |rest normal XY|.
Blender X = fingers, Y = thumb side, Z = back of the hand (same convention as V9/V10).
"""
import bpy
import bmesh
import json
import math
import sys
from pathlib import Path
from mathutils import Vector, Quaternion

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
OUT = ROOT / 'ExportFab'
OUT.mkdir(parents=True, exist_ok=True)
PREVIEW = Path(sys.argv[sys.argv.index('--preview') + 1]) if '--preview' in sys.argv else None
bpy.ops.wm.open_mainfile(filepath=str(BASE / 'AzureDragonClaw.blend'))
scene = bpy.context.scene
mesh = bpy.data.objects['SM_AzureDragonClaw']
mesh.name = 'SK_AzureDragonClawFabV10'
mesh.vertex_groups.clear()

# V10.6 structure fix: the glTF source is split at every UV seam, 70 faces wind the wrong way and
# five slots/cuffs are open, so one-sided rendering culled whole patches (the "holes"). Weld the
# seams (UVs are per loop and survive), cap the openings, wind every face outward, and rebuild
# smooth normals with sharp creases.
bm = bmesh.new()
bm.from_mesh(mesh.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=.02)
# The mirrored halves meet at y = 0 with a small gap: zip only the open seam vertices.
seam = list({v for e in bm.edges if e.is_boundary for v in e.verts})
bmesh.ops.remove_doubles(bm, verts=seam, dist=.6)
bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
# The open palm underside (x 13.7 -> 42.2) is bounded partly by non-manifold flaps, so holes_fill
# skips it (rim in source-specific coordinates). V10.6 closed it with ONE flat polygon, which read as
# a flat slab (and its UVs sat on a blank atlas corner). V10.9 fills it with a sculpted palm: the rim
# is densified, the opening triangulated with interior points, heights interpolated harmonically
# from the rim, and a relief added (heel, side and finger-root pads, central hollow, two creases)
# that fades out toward the rim. Palm side is -Z; units are source units (x5 in game).
PALM_RIM = [(13.7, -11.09, .16), (13.7, -9.44, -2.86), (13.7, -7.25, -5.56), (13.7, -5.51, -6.28),
            (13.7, -3.78, -6.99), (13.7, 0., -6.99), (13.7, 3.78, -6.99), (13.7, 5.51, -6.28),
            (13.7, 7.25, -5.56), (13.7, 9.44, -2.86), (13.7, 11.09, .16), (28.28, 11.31, -5.32),
            (31.72, 11.56, -5.63), (35.16, 11.31, -5.93), (42.07, 8.05, -4.69), (42.21, 0., -4.69),
            (42.07, -8.05, -4.69), (35.16, -11.31, -5.93), (31.72, -11.56, -5.63), (28.28, -11.31, -5.32)]
PALM_STEP = 1.  # V10.10: coarser before the Catmull-Clark level below (was .7)
PALM_FINGER_Y = (-8.39, 0., 8.39)  # ring / middle / index roots (finger-landmarks.json)


def _ss(a, b, x):
    t = min(1., max(0., (x - a) / (b - a)))
    return t * t * (3. - 2. * t)


def _bump(x, y, cx, cy, rx, ry, h):
    return h * max(0., 1. - ((x - cx) / rx) ** 2 - ((y - cy) / ry) ** 2) ** 2


def palm_relief(x, y):
    """Outward (-Z) palm relief: pads raise, the hollow and creases sink."""
    pads = (_bump(x, y, 18.6, 0., 5.2, 7.2, 1.5)                                   # heel
            + _bump(x, y, 24.5, 7.4, 6.6, 3.7, 2.0) + _bump(x, y, 24.5, -7.4, 6.6, 3.7, 1.8)  # side pads
            + sum(_bump(x, y, 38.9, fy, 3.7, 2.9, 1.25) for fy in PALM_FINGER_Y))  # finger roots
    hollow = 1.0 * math.exp(-((x - 26.0) / 4.4) ** 2 - (y / 4.2) ** 2)
    transverse = .4 * math.exp(-((x - (35.0 + .015 * y * y)) / 1.0) ** 2) * (1. - _ss(8.5, 11., abs(y)))
    q = math.sqrt(((x - 24.5) / 6.6) ** 2 + ((abs(y) - 7.4) / 3.7) ** 2)
    side = .4 * math.exp(-((q - 1.08) / .22) ** 2) * _ss(.8, -.6, abs(y) - 7.4)
    return pads - hollow - transverse - side


def sculpt_palm(bm, rim):
    from mathutils import geometry
    # Densify the rim: splitting the existing edges keeps the neighbouring faces closed.
    ring, touched = [], set()
    for a, b in zip(rim, rim[1:] + rim[:1]):
        ring.append(a)
        edge = bm.edges.get((a, b))
        if edge is None:
            raise RuntimeError('AZURE_FAB_PALM: rim edge missing')
        touched.update(edge.link_faces)
        cuts, cur = int(edge.calc_length() / PALM_STEP), a
        for k in range(1, cuts + 1):
            prev, t = (k - 1) / (cuts + 1), k / (cuts + 1)
            _, vert = bmesh.utils.edge_split(edge, cur, (t - prev) / (1. - prev))
            edge, cur = bm.edges.get((vert, b)), vert
            ring.append(vert)
    bmesh.ops.triangulate(bm, faces=[f for f in touched if f.is_valid and len(f.verts) > 4],
                          quad_method='BEAUTY', ngon_method='BEAUTY')
    pts = [Vector((v.co.x, v.co.y)) for v in ring]
    n = len(pts)

    def rim_dist(p):
        best = 1.e9
        for i in range(n):
            a, ab = pts[i], pts[(i + 1) % n] - pts[i]
            t = max(0., min(1., (p - a).dot(ab) / max(ab.length_squared, 1.e-9)))
            best = min(best, (a + ab * t - p).length)
        return best

    def inside(p):
        hit = False
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            if (a.y > p.y) != (b.y > p.y) and p.x < a.x + (p.y - a.y) * (b.x - a.x) / (b.y - a.y):
                hit = not hit
        return hit

    lo = Vector((min(p.x for p in pts), min(p.y for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts)))
    row = PALM_STEP * .866
    inner = []
    for iy in range(int((hi.y - lo.y) / row) + 2):
        for ix in range(int((hi.x - lo.x) / PALM_STEP) + 2):
            p = Vector((lo.x + (ix + .5 * (iy % 2)) * PALM_STEP, lo.y + iy * row))
            if inside(p) and rim_dist(p) > .55 * PALM_STEP:
                inner.append(p)
    out_co, _, out_faces, orig, _, _ = geometry.delaunay_2d_cdt(pts + inner, [], [list(range(n))], 1, 1.e-6)
    m = len(out_co)
    z, fixed, nbrs = [0.] * m, [False] * m, [set() for _ in range(m)]
    for i, ids in enumerate(orig):
        on_rim = [k for k in ids if k < n]
        if on_rim:
            z[i], fixed[i] = ring[on_rim[0]].co.z, True
    for f in out_faces:
        for a, b in zip(f, f[1:] + f[:1]):
            nbrs[a].add(b)
            nbrs[b].add(a)
    for i in range(m):
        if not fixed[i]:
            w = [(1. / max(.01, (Vector(out_co[i]) - pts[k]).length_squared), ring[k].co.z) for k in range(n)]
            z[i] = sum(a * b for a, b in w) / sum(a for a, _ in w)
    for _ in range(400):  # harmonic heights from the rim
        for i in range(m):
            if not fixed[i] and nbrs[i]:
                z[i] = sum(z[j] for j in nbrs[i]) / len(nbrs[i])
    # The finger-root plates hang into the opening (z -4.3..-5.0 at x 29..37): keep the sculpted palm
    # below every original surface so nothing pokes through it.
    # The limit field is eroded over two rings (closing gaps between plates), then slope-limited so the
    # palm eases down under the plates instead of stepping, and applied with a smooth minimum.
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromBMesh(bm)
    limit = [1.e3] * m
    for i in range(m):
        if not fixed[i]:
            hit = bvh.ray_cast(Vector((out_co[i][0], out_co[i][1], -60.)), Vector((0., 0., 1.)), 120.)[0]
            if hit is not None:
                limit[i] = hit.z - 1.  # V10.10: clearance for the Catmull-Clark level (palm relaxes inward)
    for _ in range(2):
        limit = [min([limit[i]] + [limit[j] for j in nbrs[i]]) for i in range(m)]
    flat = [Vector(c) for c in out_co]
    for _ in range(40):
        for i in range(m):
            for j in nbrs[i]:
                limit[i] = min(limit[i], limit[j] + .45 * (flat[i] - flat[j]).length)
    # V10.10: clamping flattened the palm into a plateau under the plates. Instead lower the whole
    # relief there by a dilated, blurred offset (pads and creases survive), then clamp only as a guard.
    height = [z[i] if fixed[i] else z[i] - _ss(0., 2.6, rim_dist(flat[i])) * palm_relief(flat[i].x, flat[i].y)
              for i in range(m)]
    lower = [0. if fixed[i] else max(0., height[i] - limit[i]) for i in range(m)]
    for _ in range(2):
        lower = [0. if fixed[i] else max([lower[i]] + [lower[j] for j in nbrs[i]]) for i in range(m)]
    for _ in range(6):
        lower = [0. if fixed[i] else (lower[i] + sum(lower[j] for j in nbrs[i])) / (1 + len(nbrs[i])) for i in range(m)]
    verts = []
    for i in range(m):
        if fixed[i]:
            verts.append(ring[[k for k in orig[i] if k < n][0]])
        else:
            verts.append(bm.verts.new((flat[i].x, flat[i].y, min(height[i] - lower[i], limit[i]))))
    uv = bm.loops.layers.uv.active
    added = 0
    for f in out_faces:
        try:
            face = bm.faces.new([verts[i] for i in f])
        except ValueError:
            continue
        added += 1
        for loop in face.loops:  # flat-normal atlas texel: the sculpt itself carries the form
            loop[uv].uv = (.002, .002)
    print('AZURE_FAB_PALM: rim %d, interior %d, faces %d' % (n, len(inner), added))


if any(e.is_boundary for e in bm.edges):
    from mathutils.kdtree import KDTree
    bm.verts.ensure_lookup_table()
    tree = KDTree(len(bm.verts))
    for v in bm.verts:
        tree.insert(v.co, v.index)
    tree.balance()
    rim = []
    for p in PALM_RIM:
        _, index, dist = tree.find(Vector(p))
        rim.append(bm.verts[index] if dist < .05 else None)
    if all(rim) and len(set(rim)) == len(rim):
        sculpt_palm(bm, rim)
    else:
        print('AZURE_FAB_PALM_RIM: rim vertices not found, left open')
print('AZURE_FAB_BOUNDARY_EDGES', sum(1 for e in bm.edges if e.is_boundary))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(mesh.data)
bm.free()
if mesh.data.has_custom_normals:
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
for poly in mesh.data.polygons:
    poly.use_smooth = True
if hasattr(mesh.data, 'set_sharp_from_angle'):
    mesh.data.set_sharp_from_angle(angle=math.radians(50.))
mesh.data.update()
landmarks = json.loads((BASE / 'Export/finger-landmarks.json').read_text(encoding='utf-8'))
low, high = -19.08791732788086, 20.21254539489746  # same frame as author_model.py / V9
scale = 125. / (high - low)
pivot = low + (high - low) * .36
height_center = (-3.97971248626709 + 5.481351852416992) * .5


def transform(p):
    return Vector(((p[2] - pivot) * scale, p[0] * scale, (p[1] - height_center) * scale))


def ease(t):
    t = min(1., max(0., t))
    return t * t * (3. - 2. * t)


def smooth(a, b, x):
    return ease((x - a) / (b - a))


digits = []
LABELS = ['Pinky', 'Ring', 'Middle', 'Index', 'Thumb']
for i, landmark in enumerate(landmarks):
    outer = i in (0, 4)
    center = landmark['center']
    base = transform([center[0] * (.70 if outer else .90), .35, 2.5 if outer else 5.])
    nail = transform([center[0], .15, landmark['min'][2] + .35])
    tip = transform(landmark['tip'])
    # The nail rides its own terminal bone; the skin bends at the real knuckles.
    digits.append(dict(name='digit_%02d' % (i + 1), points=[base, base.lerp(nail, .49), nail, tip],
                       outer=outer, label=LABELS[i]))


def nearest_digit(p):
    """V9 rule: the digit whose base->nail segment p hugs, and p's normalised place along it."""
    best = None
    for i, d in enumerate(digits):
        a, b = d['points'][0], d['points'][2]
        seg = b - a
        t = max(0., min(1., (p - a).dot(seg) / seg.length_squared))
        near = a + seg * t
        key = (p.y - near.y) ** 2 + .15 * (p.x - near.x) ** 2
        if best is None or key < best[0]:
            best = (key, i, t)
    return best[1], best[2]


def is_talon(p):
    return p.x >= 3. and p.x >= digits[nearest_digit(p)[0]]['points'][2].x - .35


# ---- V10.10 refinement ---------------------------------------------------------------------------
# The Fab claw is low-poly for its x5 game size (6-sided finger prisms, metre-wide flat panels on the
# hand and forearm). Join triangles into quads, crease plate borders by angle (semi-sharp, so they
# read as rounded bevels rather than hard facets; talons fully creased so they keep their points) and
# apply one Catmull-Clark level with linear UVs. Skin, colours and rest UVs are rebuilt per vertex
# below; the Fab normal atlas keeps its UV layout.
def refine(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.join_triangles(bm, faces=list(bm.faces), cmp_uvs=True, angle_face_threshold=math.radians(30.),
                             angle_shape_threshold=math.radians(40.))
    crease = bm.edges.layers.float.get('crease_edge') or bm.edges.layers.float.new('crease_edge')
    for e in bm.edges:
        if len(e.link_faces) != 2 or all(is_talon(v.co) for v in e.verts):
            e[crease] = 1.
            continue
        angle = math.degrees(e.calc_face_angle(0.))
        e[crease] = .85 if angle > 55. else (.4 if angle > 30. else 0.)
    bm.to_mesh(obj.data)
    bm.free()
    sub = obj.modifiers.new('FabRefineV10', 'SUBSURF')
    sub.levels = sub.render_levels = 1
    sub.uv_smooth = 'NONE'
    sub.use_creases = True
    graph = bpy.context.evaluated_depsgraph_get()
    refined = bpy.data.meshes.new_from_object(obj.evaluated_get(graph))
    obj.modifiers.remove(sub)
    old, obj.data = obj.data, refined
    bpy.data.meshes.remove(old)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    if hasattr(obj.data, 'set_sharp_from_angle'):
        obj.data.set_sharp_from_angle(angle=math.radians(60.))
    obj.data.update()
    print('AZURE_FAB_REFINED', json.dumps(dict(verts=len(obj.data.vertices),
                                               tris=sum(len(p.vertices) - 2 for p in obj.data.polygons))))


refine(mesh)

# ---- armature: V9 layout plus talon-tip leaves --------------------------------------------
bpy.ops.object.select_all(action='DESELECT')
data = bpy.data.armatures.new('AzureDragonClawFabSkeletonV10')
rig = bpy.data.objects.new('AzureDragonClawFabRigV10', data)
scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
root = data.edit_bones.new('root')
root.head, root.tail = Vector((-45, 0, 0)), Vector((-12, 0, 0))
root.align_roll(Vector((0, 0, 1)))
palm = data.edit_bones.new('palm')
palm.head, palm.tail, palm.parent = root.tail, Vector((27, 0, 0)), root
palm.align_roll(Vector((0, 0, 1)))
# V10.10: forearm twist helper, a new leaf under root (palm keeps its parent, so the saved skeleton
# only gains a bone); it takes half of the wrist roll so the forearm turns instead of the wrist snapping.
twist = data.edit_bones.new('forearm_twist')
twist.head, twist.tail, twist.parent = Vector((-30, 0, 0)), root.tail, root
twist.align_roll(Vector((0, 0, 1)))
for d in digits:
    parent = palm
    for j in range(3):
        b = data.edit_bones.new('%s_%02d' % (d['name'], j + 1))
        b.head, b.tail = d['points'][j], d['points'][j + 1]
        b.parent, b.use_connect = parent, False
        b.align_roll(Vector((0, 0, 1)))
        parent = b
    # Unweighted talon-point leaves: 01..04 feed the trails, all five anchor the talon flames.
    tip_dir = (d['points'][3] - d['points'][2]).normalized()
    t = data.edit_bones.new('%s_tip' % d['name'])
    t.head, t.tail = d['points'][3], d['points'][3] + tip_dir * 2.
    t.parent, t.use_connect = parent, False
    t.align_roll(Vector((0, 0, 1)))
bpy.ops.object.mode_set(mode='OBJECT')

# ---- skin (V9 recipe) + material attributes --------------------------------------------------
groups = {b.name: mesh.vertex_groups.new(name=b.name) for b in data.bones if not b.name.endswith('_tip')}
counts = {n: 0 for n in groups}


def add(index, name, value):
    if value > 1.e-6:
        groups[name].add([index], value, 'REPLACE')
        counts[name] += 1


me = mesh.data
n_verts = len(me.vertices)
along = [0.] * n_verts
talon = [0.] * n_verts
joint = [0.] * n_verts
for v in me.vertices:
    p = v.co
    if p.x < 3.:
        blend = ease((p.x + 17.) / 20.)
        tw = ease((p.x + 36.) / 18.)  # V10.10: root -> forearm twist -> palm
        add(v.index, 'root', (1. - blend) * (1. - tw))
        add(v.index, 'forearm_twist', (1. - blend) * tw)
        add(v.index, 'palm', blend)
        continue
    i, t = nearest_digit(p)
    d = digits[i]
    pts = d['points']
    strength = ease((p.x - pts[0].x + 4.) / 9.)
    if p.x >= pts[2].x - .35:
        add(v.index, d['name'] + '_03', 1.)
        talon[v.index] = 1.
        along[v.index] = max(0., min(1., (p - pts[2]).dot((pts[3] - pts[2]).normalized()) / (pts[3] - pts[2]).length))
    else:
        a = ease((t - .36) / .26)  # V10.10: wider knuckle blends (were .40/.18 and .88/.12)
        b = ease((t - .84) / .18)
        add(v.index, 'palm', 1. - strength)
        for j, weight in enumerate((1. - a, a * (1. - b), a * b)):
            add(v.index, '%s_%02d' % (d['name'], j + 1), strength * weight)
        along[v.index] = t * strength
        length = (pts[2] - pts[0]).length
        s = t * length
        joint[v.index] = strength * max(math.exp(-((s - .49 * length) / 1.6) ** 2), math.exp(-((s - length) / 1.4) ** 2))

# V10.10: A = 0 on the sculpted palm (its UV0 sits on the flat atlas texel), 1 elsewhere; the material
# gives the palm stronger pebble-scale detail since the Fab atlas has none there.
atlas = me.uv_layers[0].data
loops_at, palm_at = [0] * n_verts, [0] * n_verts
for loop in me.loops:
    loops_at[loop.vertex_index] += 1
    uv0 = atlas[loop.index].uv
    palm_at[loop.vertex_index] += abs(uv0.x - .002) < 1.e-4 and abs(uv0.y - .002) < 1.e-4
cols = me.color_attributes.new('Col', 'BYTE_COLOR', 'POINT')
for v in me.vertices:
    forearm = 1. - smooth(-44., -2., v.co.x)  # 1 at the far guard, 0 from the wrist on
    on_palm = loops_at[v.index] and palm_at[v.index] == loops_at[v.index]
    cols.data[v.index].color = (along[v.index], talon[v.index], forearm, 0. if on_palm else 1.)

TILE_CM = 22.
uv_xy, uv_zj, uv_n = (me.uv_layers.new(name=n) for n in ('RestXY', 'RestZJoint', 'RestN'))
for poly in me.polygons:
    for li in poly.loop_indices:
        vi = me.loops[li].vertex_index
        co, n = me.vertices[vi].co, me.vertices[vi].normal
        uv_xy.data[li].uv = (co.x / TILE_CM, co.y / TILE_CM)
        uv_zj.data[li].uv = (co.z / TILE_CM, joint[vi])
        uv_n.data[li].uv = (abs(n.x), abs(n.y))
me.uv_layers.active_index = 0
for i, layer in enumerate(me.uv_layers):
    layer.active_render = i == 0

modifier = mesh.modifiers.new('FabClawSkinV10', 'ARMATURE')
modifier.object = rig
modifier.use_deform_preserve_volume = False
mesh.parent = rig

# ---- the V10.1 gesture, mapped onto five digits ------------------------------------------------
# V10.10: frames 0-36 are the rake (0.6 s); 36-276 a seamless 4 s idle loop (C++ samples it on its
# own clock between rakes, starting at frame 36 so a finished rake flows straight into it).
IDLE_START, IDLE_FRAMES, IDLE_STEP = 36, 240, 10
scene.render.fps, scene.frame_start, scene.frame_end = 60, 0, IDLE_START + IDLE_FRAMES
# frame, (proximal, middle, distal curl deg), spread (+ open), wrist pitch (+ flex down), wrist roll
KEYS = [(0, (8., 30., 18.), .45, 0., 0.),       # summoned idle: relaxed hook
        (8, (-6., 12., 6.), .85, -14., -4.),     # rising, opening
        (12, (-12., 0., -4.), 1.0, -28., -8.),   # windup apex: talons splayed, wrist cocked back
        (16, (-10., 4., 0.), .95, -16., -4.),    # swiping in, still open, wrist starts to whip
        (18, (4., 30., 14.), .45, 6., 2.),       # contact: the snap begins exactly here
        # Same beats as V10.1; the Fab digits are short with long nails, so the hook closes less
        # (V10.1's 62/40 deg folds these talons into a fist).
        (20, (14., 46., 24.), -.25, 28., 8.),    # raking hook (talons turned in, never a fist)
        (22, (17., 52., 28.), -.32, 36., 11.),   # V10.10: overshoot past the hook...
        (24, (13., 43., 22.), -.20, 34., 10.),   # ...settling into the held hook (follow-through)
        (30, (9., 34., 18.), .15, 14., 4.),      # releasing on the recovery arc
        (36, (8., 30., 18.), .45, 0., 0.)]
# Index leads the rake, the outer digits trail; distal joints lag the snap and lead the release.
LEAD = {'Index': -.4, 'Middle': 0., 'Ring': .4, 'Pinky': .8, 'Thumb': 1.}
SPREAD_DEG = {'Pinky': -12., 'Ring': -6., 'Middle': 0., 'Index': 6., 'Thumb': 14.}
THUMB_SCALE = (.6, .75, .9)


def stamp(frame, label, k):
    if frame in (16, 18, 20, 22, 24):
        return frame + LEAD[label] + (.6 * k if frame in (18, 20, 22) else 0.)
    if frame == 30:
        return frame - .6 * k
    return float(frame)


# Idle loop: slow breathing curl, spread and wrist sway, each digit on its own phase. Every wave is
# zero at the loop ends (period 4 s or 2 s), so the loop starts and ends exactly on the idle pose.
IDLE_PHASE = {'Index': 0., 'Middle': .9, 'Ring': 1.8, 'Pinky': 2.7, 'Thumb': 4.1}
IDLE_CURL = (3., 6., 5.)


def idle_wave(frame, phase, harmonic=1):
    w = 2. * math.pi * harmonic / IDLE_FRAMES
    return math.sin(w * (frame - IDLE_START) + phase) - math.sin(phase)


IDLE_KEYFRAMES = range(IDLE_START + IDLE_STEP, IDLE_START + IDLE_FRAMES + 1, IDLE_STEP)


bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='POSE')
for i, d in enumerate(digits):
    for k in range(3):
        pb = rig.pose.bones['%s_%02d' % (d['name'], k + 1)]
        pb.rotation_mode = 'QUATERNION'
        direction = (d['points'][k + 1] - d['points'][k]).normalized()
        curl = Vector((0, -.12 if d['label'] == 'Thumb' else 0., -1.)).normalized()
        bind = pb.bone.matrix_local.to_quaternion().inverted()
        bend = (bind @ direction.cross(curl)).normalized()
        gather = (bind @ Vector((0, 0, 1))).normalized()

        def pose(curl_deg, spread, frame):
            if d['outer'] and k == 0:
                # V10.10: the outer digits are separate shells set into the hand; pulled far back and
                # splayed (windup) their roots opened and crumpled, so limit extension and splay.
                curl_deg, spread = max(curl_deg, -3.), spread * .55
            value = curl_deg * (THUMB_SCALE[k] if d['label'] == 'Thumb' else 1.)
            q = Quaternion(bend, math.radians(value))
            if k == 0:
                q = Quaternion(gather, math.radians(SPREAD_DEG[d['label']] * spread)) @ q
            pb.rotation_quaternion = q
            pb.keyframe_insert('rotation_quaternion', frame=frame, group=pb.name)

        for frame, curls, spread, _, _ in KEYS:
            pose(curls[k], spread, stamp(frame, d['label'], k))
        phase = IDLE_PHASE[d['label']]
        for frame in IDLE_KEYFRAMES:
            breath = .7 * idle_wave(frame, phase + .5 * k) + .3 * idle_wave(frame, phase * 1.3 + k, 2)
            pose(KEYS[0][1][k] + IDLE_CURL[k] * breath, KEYS[0][2] + .06 * idle_wave(frame, phase + 1.1), float(frame))
palm_pb = rig.pose.bones['palm']
palm_pb.rotation_mode = 'QUATERNION'
wrist_axis = (palm_pb.bone.matrix_local.to_quaternion().inverted() @ Vector((0, 1, 0))).normalized()
roll_axis = (palm_pb.bone.matrix_local.to_quaternion().inverted() @ Vector((1, 0, 0))).normalized()
twist_pb = rig.pose.bones['forearm_twist']
twist_pb.rotation_mode = 'QUATERNION'
twist_axis = (twist_pb.bone.matrix_local.to_quaternion().inverted() @ Vector((1, 0, 0))).normalized()
wrist_keys = [(frame, pitch, roll) for frame, _, _, pitch, roll in KEYS]
wrist_keys += [(frame, 3.5 * idle_wave(frame, .4), 2.5 * idle_wave(frame, 2.)) for frame in IDLE_KEYFRAMES]
for frame, pitch, roll in wrist_keys:
    palm_pb.rotation_quaternion = Quaternion(roll_axis, math.radians(roll)) @ Quaternion(wrist_axis, math.radians(pitch))
    palm_pb.keyframe_insert('rotation_quaternion', frame=frame, group='palm')
    twist_pb.rotation_quaternion = Quaternion(twist_axis, math.radians(roll * .5))
    twist_pb.keyframe_insert('rotation_quaternion', frame=frame, group='forearm_twist')
bpy.ops.object.mode_set(mode='OBJECT')
action = rig.animation_data.action
action.name = 'A_AzureDragonClawFabRakeV10'
action.use_fake_user = True


def iter_fcurves(act):
    if hasattr(act, 'fcurves') and len(getattr(act, 'fcurves', [])):
        yield from act.fcurves
        return
    for slot in act.slots:
        for layer in act.layers:
            for strip in layer.strips:
                bag = strip.channelbag(slot)
                if bag:
                    yield from bag.fcurves


for fc in iter_fcurves(action):
    for key in fc.keyframe_points:
        key.interpolation = 'BEZIER'
        key.handle_left_type = key.handle_right_type = 'AUTO_CLAMPED'
    fc.update()

# ---- preview (authoring check only, Blender workbench; not a UE render) ----------------------
if PREVIEW:
    PREVIEW.mkdir(parents=True, exist_ok=True)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'VERTEX'
    scene.render.resolution_x, scene.render.resolution_y = 640, 480
    target = Vector((20, 0, 0))
    for frame in (0, 12, 18, 21):
        scene.frame_set(frame)
        for view, off in (('side', (10, -190, 10)), ('persp', (110, -130, 95)), ('front', (210, -30, 20))):
            cam.location = target + Vector(off)
            cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = str(PREVIEW / ('fab_%s_%02d.png' % (view, frame)))
            bpy.ops.render.render(write_still=True)

# ---- export ------------------------------------------------------------------------------------
rig.animation_data.action = None
for pb in rig.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = Quaternion()
scene.frame_set(0)
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
mesh.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
common = dict(use_selection=True, object_types={'MESH', 'ARMATURE'}, axis_forward='-Y', axis_up='Z',
              add_leaf_bones=False, mesh_smooth_type='EDGE', use_tspace=False, apply_scale_options='FBX_SCALE_ALL',
              armature_nodetype='NULL', embed_textures=False, colors_type='LINEAR')
bpy.ops.export_scene.fbx(filepath=str(OUT / 'SK_AzureDragonClawFabV10.fbx'), bake_anim=False, **common)
rig.animation_data.action = action
if getattr(action, 'slots', None):
    rig.animation_data.action_slot = action.slots[0]
scene.frame_set(0)
bpy.ops.export_scene.fbx(filepath=str(OUT / 'A_AzureDragonClawFabRakeV10.fbx'), bake_anim=True, bake_anim_use_all_actions=False,
                         bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True, bake_anim_step=1.,
                         bake_anim_simplify_factor=0., **common)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'AzureDragonClawFabV10.blend'))
manifest = dict(revision='10.10', source='Fab Dragon Claw (CaptainHC) via AzureDragonClaw.blend', bones=len(data.bones),
                digits=5, joints_per_digit=3, tip_bones=['%s_tip' % d['name'] for d in digits],
                uv_channels=['UVMap (Fab atlas)', 'RestXY', 'RestZJoint', 'RestN'], rest_tile_cm=TILE_CM,
                animation_seconds=.6, phase_frames=dict(lead=[0, 12], swipe=[12, 24], recovery=[24, 36], contact=18),
                idle_loop=dict(start_frame=IDLE_START, frames=IDLE_FRAMES, seconds=IDLE_FRAMES / 60.),
                keys=KEYS, weighted_vertices=counts, triangles=sum(len(p.vertices) - 2 for p in me.polygons),
                mesh=str(OUT / 'SK_AzureDragonClawFabV10.fbx'), animation=str(OUT / 'A_AzureDragonClawFabRakeV10.fbx'),
                rendered=False, runtime_tested=False)
(OUT / 'rig.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('AZURE_DRAGON_CLAW_FAB_V10_EXPORTED', json.dumps(dict(bones=len(data.bones), tris=manifest['triangles'])), flush=True)
