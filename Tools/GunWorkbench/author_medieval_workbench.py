# Medieval survival workbench - full author pass (2026-09-28).
#
# Builds the complete gun_workbench_table restyle as separate editable parts in
# one blend, renders previews, then joins by material and exports the merged
# FBX for the single-mesh build-prefab pipeline.
#
# Hard contracts kept identical to the live asset:
#   - mesh-local origin at floor center; mat zone x[0.55,1.09] y[-0.65,0.65]
#     top face 0.953 m (gun-assembly.json anchors unchanged)
#   - bbox x[-1.209,1.209] y[-1.303,1.287] z[0,1.576] so ComputeTransform
#     keeps placed instances where they are
#   - camera sight-line corridor (x 0.24->0.82, y~0) stays clear
# Materials/slots: Oak, DarkIron, Rope (bound to library assets at import) +
# Leather, Clay (new materials with imported textures).
import bpy, bmesh, math, random, os, json
from mathutils import Vector

random.seed(20260929)

ROOT = r'D:\FPS3D\FPSGAME\SourceAssets\GunWorkbenchMedieval20260928'
AUTH = os.path.join(ROOT, 'Authored')
TEX = r'D:\FPS3D\FPSGAME\Saved\GunWorkbench20260927\texpreview'
os.makedirs(AUTH, exist_ok=True)

BBOX_TARGET = ((-1.209, -1.303, 0.0), (1.209, 1.287, 1.576))

# factory-startup scene ships a default cube; clear meshes before building
for _ob in list(bpy.context.scene.objects):
    if _ob.type == 'MESH':
        bpy.data.objects.remove(_ob, do_unlink=True)

# ---------------------------------------------------------------- materials
def img_node(nt, path, box=True, blend=0.6, noncolor=False):
    t = nt.nodes.new('ShaderNodeTexImage')
    t.image = bpy.data.images.load(path)
    if box:
        t.projection = 'BOX'
        t.projection_blend = blend
    if noncolor:
        t.image.colorspace_settings.name = 'Non-Color'
    return t

def preview_material(name, base, rough=None, normal=None, roughv=0.85,
                     metal=0.0, blend=0.6):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = roughv
    b.inputs['Metallic'].default_value = metal
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    if base:
        t = img_node(nt, base, blend=blend)
        nt.links.new(mp.outputs['Vector'], t.inputs['Vector'])
        nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    if rough:
        t = img_node(nt, rough, blend=blend, noncolor=True)
        nt.links.new(mp.outputs['Vector'], t.inputs['Vector'])
        nt.links.new(t.outputs['Color'], b.inputs['Roughness'])
    if normal:
        t = img_node(nt, normal, blend=blend, noncolor=True)
        nv = nt.nodes.new('ShaderNodeNormalMap')
        nv.inputs['Strength'].default_value = 0.7
        nt.links.new(mp.outputs['Vector'], t.inputs['Vector'])
        nt.links.new(t.outputs['Color'], nv.inputs['Color'])
        nt.links.new(nv.outputs['Normal'], b.inputs['Normal'])
    return m

SLOTS = ['Oak', 'DarkIron', 'Rope', 'Leather', 'Clay']
MATS = {
    'Oak': preview_material('Oak', os.path.join(TEX, 'oak_basecolor.png'),
                            os.path.join(TEX, 'oak_rough.png'),
                            os.path.join(TEX, 'oak_normal.png')),
    'DarkIron': preview_material('DarkIron', os.path.join(TEX, 'iron_basecolor.png'),
                                 os.path.join(TEX, 'iron_rough.png'),
                                 os.path.join(TEX, 'iron_normal.png'), metal=0.75,
                                 blend=0.5),
    'Rope': preview_material('Rope', os.path.join(TEX, 'rope_basecolor.png'),
                             os.path.join(TEX, 'rope_rough.png'), blend=0.0),
    'Leather': preview_material('Leather', os.path.join(TEX, 'leather_basecolor.png'),
                                os.path.join(TEX, 'leather_rough.png'),
                                os.path.join(TEX, 'leather_normal.png'), blend=0.8),
    'Clay': preview_material('Clay', os.path.join(TEX, 'clay_basecolor.png'),
                             os.path.join(TEX, 'clay_rough.png'),
                             os.path.join(TEX, 'clay_normal.png'), blend=0.8),
}

# ---------------------------------------------------------------- helpers
bevels = []
smooth = set()

def cube(name, x0, x1, y0, y1, z0, z1, slot, bev=0.0015, seg=2):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(
        (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = (x1 - x0, y1 - y0, z1 - z0)
    bpy.ops.object.transform_apply(scale=True)
    ob.data.materials.append(MATS[slot])
    if bev:
        bevels.append((ob, bev, seg))
    return ob

def cyl(name, r, depth, location, axis='Z', seg=16, slot='Oak', rot=0.0,
        smooth_on=True):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth,
                                        location=location, vertices=seg,
                                        rotation=(math.pi / 2, 0, 0)
                                        if axis == 'Y' else (0, math.pi / 2, 0)
                                        if axis == 'X' else (0, 0, rot))
    ob = bpy.context.active_object
    ob.name = name
    ob.data.materials.append(MATS[slot])
    if smooth_on:
        smooth.add(ob.name)
    return ob

def lathe(name, profile, steps, slot):
    bm = bmesh.new()
    vs = [bm.verts.new((r, 0.0, h)) for r, h in profile]
    es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
    bmesh.ops.spin(bm, geom=vs + es, axis=(0, 0, 1), cent=(0, 0, 0),
                   steps=steps, angle=2 * math.pi)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(MATS[slot])
    smooth.add(name)
    return ob

def sweep(name, p0, p1, p2, radius, sides, slot, pull=(0.004, 0.004)):
    a = Vector(p0); a.x -= pull[0]
    b = Vector(p2); b.x -= pull[1]
    pts = []
    for k in range(16):
        t = k / 15.0
        u = 1 - t
        pts.append(u * u * a + 2 * u * t * Vector(p1) + t * t * b)
    rings = []
    for idx, P in enumerate(pts):
        T = (pts[min(idx + 1, 15)] - pts[max(idx - 1, 0)]).normalized()
        U = T.cross(Vector((0, 1, 0)))
        if U.length < 1e-6:
            U = Vector((1, 0, 0))
        U = U.normalized()
        V = T.cross(U).normalized()
        rings.append([P + radius * (
            math.cos(2 * math.pi * s / sides) * U
            + math.sin(2 * math.pi * s / sides) * V) for s in range(sides)])
    bm = bmesh.new()
    bv = [[bm.verts.new(p) for p in ring] for ring in rings]
    for r in range(len(rings) - 1):
        for s in range(sides):
            s2 = (s + 1) % sides
            bm.faces.new((bv[r][s], bv[r][s2], bv[r + 1][s2], bv[r + 1][s]))
    for ring in (bv[0], bv[-1]):
        c = bm.verts.new(Vector(tuple(
            sum(v.co[i] for v in ring) / sides for i in range(3))))
        for s in range(sides):
            bm.faces.new((ring[s], ring[(s + 1) % sides], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(MATS[slot])
    smooth.add(name)
    return ob

def place(ob, x, y, z, yaw=0.0):
    ob.location = (x, y, z)
    ob.rotation_euler = (0, 0, yaw)
    return ob

# ------------------------------------------------- crate builder (v3 style)
def build_crate(prefix, cx0, cx1, cy0, cy1, cz0, height, yaw=0.0, seed=0):
    rnd = random.Random(20260900 + seed)
    xo = (cx0 + cx1) / 2; yo = (cy0 + cy1) / 2; zo = cz0
    L = cx1 - cx0; W = cy1 - cy0
    t, g = 0.012, 0.004
    rows = []
    z = zo + 0.018
    while z + t <= zo + height - 0.012:
        rows.append((z, z + t))
        z += t + g
    parts = []
    for i, (a, b) in enumerate(rows):
        parts.append(cube(prefix + 'F%d' % i, xo - L / 2 + 0.01, xo + L / 2 - 0.01,
                          yo + W / 2, yo + W / 2 + t, a, b, 'Oak'))
        parts.append(cube(prefix + 'B%d' % i, xo - L / 2 + 0.01, xo + L / 2 - 0.01,
                          yo - W / 2 - t, yo - W / 2, a, b, 'Oak'))
        parts.append(cube(prefix + 'E%d' % i, xo + L / 2, xo + L / 2 + t,
                          yo - W / 2 - t, yo + W / 2 + t, a, b, 'Oak'))
        parts.append(cube(prefix + 'W%d' % i, xo - L / 2 - t, xo - L / 2,
                          yo - W / 2 - t, yo + W / 2 + t, a, b, 'Oak'))
    for k in range(3):
        a = xo - L / 2 + 0.045 + k * (L - 0.09) / 3
        parts.append(cube(prefix + 'bt%d' % k, a, a + (L - 0.09) / 3 * 0.92,
                          yo - W / 2 + 0.01, yo + W / 2 - 0.01, zo + 0.004,
                          zo + 0.016, 'Oak'))
    parts.append(cube(prefix + 'lid', xo - L / 2 - 0.008, xo + L / 2 + 0.008,
                      yo - W / 2 - 0.012, yo + W / 2 + 0.012,
                      zo + height - 0.012, zo + height, 'Oak', bev=0.002, seg=3))
    for sx, sy in ((xo - L / 2 - t, yo - W / 2 - t), (xo + L / 2, yo - W / 2 - t),
                   (xo - L / 2 - t, yo + W / 2), (xo + L / 2, yo + W / 2)):
        parts.append(cube(prefix + 'csA', sx, sx + 0.014, sy, sy + 0.030,
                          zo + 0.004, zo + height - 0.014, 'DarkIron', bev=0.001))
        parts.append(cube(prefix + 'csB', sx, sx + 0.030, sy, sy + 0.014,
                          zo + 0.004, zo + height - 0.014, 'DarkIron', bev=0.001))
    for sx in (xo - L / 2 + 0.05, xo + L / 2 - 0.07):
        parts.append(cube(prefix + 'lsT', sx, sx + 0.020, yo - W / 2 - 0.012,
                          yo + W / 2 + 0.012, zo + height, zo + height + 0.010,
                          'DarkIron', bev=0.001))
    # rope handle
    bpy.ops.mesh.primitive_torus_add(major_radius=0.055, minor_radius=0.0058,
                                     major_segments=40, minor_segments=10,
                                     location=(xo, yo, zo + height))
    arc = bpy.context.active_object
    arc.name = prefix + 'rope'
    bm = bmesh.new(); bm.from_mesh(arc.data)
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        th = math.atan2(v.co.y, v.co.x)
        c = Vector((0.055 * math.cos(th), 0.055 * math.sin(th), 0.0))
        d = v.co - c
        if d.length > 1e-9:
            v.co = c + d.normalized() * (
                0.0058 * (1.0 + 0.13 * math.sin(3 * th + v.co.z * 40)))
    bm.to_mesh(arc.data); bm.free()
    arc.rotation_euler = (math.pi / 2, 0, 0)
    bpy.ops.object.transform_apply(rotation=True)
    bm = bmesh.new(); bm.from_mesh(arc.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < 0.0005],
                     context='VERTS')
    bm.to_mesh(arc.data); bm.free()
    arc.data.materials.append(MATS['Rope'])
    smooth.add(arc.name)
    parts.append(arc)
    for sx in (xo - 0.055, xo + 0.055):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.009,
                                             location=(sx, yo, zo + height + 0.003))
        k = bpy.context.active_object
        k.name = prefix + 'knot'
        k.scale = (1, 1, 0.75)
        bpy.ops.object.transform_apply(scale=True)
        k.data.materials.append(MATS['Rope'])
        smooth.add(k.name)
        parts.append(k)
    del rnd
    if yaw:
        from mathutils import Matrix
        R = Matrix.Rotation(yaw, 4, 'Z')
        for p in parts:
            bm = bmesh.new(); bm.from_mesh(p.data)
            bm.verts.ensure_lookup_table()
            for v in bm.verts:
                v.co = Vector((xo, yo, 0)) + R @ (v.co - Vector((xo, yo, 0)))
            bm.to_mesh(p.data); bm.free()
    return parts

# ------------------------------------------------- main bench (east arm)
MX0, MX1 = 0.45, 1.209
TOP0, TOP1 = 0.895, 0.945
N = 5
w = (MX1 - MX0) / N
for i in range(N):
    zj = TOP1 + random.uniform(-0.0008, 0.0008)
    cube('mainPlank%d' % i, MX0 + i * w + 0.002, MX0 + (i + 1) * w - 0.002,
         -0.70, 0.86, TOP0, zj, 'Oak')
for yy0, yy1 in ((-0.66, -0.63), (0.815, 0.845)):
    cube('mainApron', MX0 + 0.04, MX1 - 0.04, yy0, yy1, 0.845, TOP0, 'Oak')
for lx in (MX0 + 0.01, MX1 - 0.099):
    for ly in (-0.69, 0.75):
        cube('mainLeg', lx, lx + 0.09, ly, ly + 0.09, 0.0, 0.845, 'Oak',
             bev=0.002, seg=3)
for sc in (-0.31, 0.07, 0.45):
    cube('mainShelf', MX0 + 0.04, MX1 - 0.04, sc - 0.17, sc + 0.17, 0.30, 0.33,
         'Oak')
build_crate('store', 0.65, 0.99, -0.37, -0.15, 0.33, 0.15, seed=1)

# ------------------------------------------------- leather work mat
cube('matBase', 0.55, 1.09, -0.65, 0.65, 0.946, 0.953, 'Leather',
     bev=0.003, seg=3)
for (rx0, rx1, ry0, ry1) in ((0.570, 1.070, -0.630, -0.616),
                             (0.570, 1.070, 0.616, 0.630),
                             (0.570, 0.584, -0.616, 0.616),
                             (1.056, 1.070, -0.616, 0.616)):
    cube('matRim', rx0, rx1, ry0, ry1, 0.953, 0.9545, 'Leather', bev=0.001)

# ------------------------------------------------- wooden front vise
cube('viseJaw', 0.70, 0.86, -0.865, -0.705, 0.815, 0.945, 'Oak',
     bev=0.002, seg=3)
for rx in (0.727, 0.833):
    cyl('viseRod', 0.006, 0.30, (rx, -0.845, 0.850), axis='Y', slot='DarkIron')
cyl('viseScrew', 0.009, 0.31, (0.780, -0.855, 0.885), axis='Y', slot='DarkIron')
cyl('viseT', 0.011, 0.17, (0.780, -0.985, 0.885), axis='X', slot='Oak')
for ex in (0.695, 0.865):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.016,
                                         location=(ex, -0.985, 0.885))
    e = bpy.context.active_object
    e.name = 'viseEnd'
    e.data.materials.append(MATS['Oak'])
    smooth.add(e.name)

# ------------------------------------------------- torch stand
cube('postBase', 0.385, 0.635, 0.815, 1.065, 0.0, 0.025, 'DarkIron',
     bev=0.002, seg=3)
cube('post', 0.47, 0.55, 0.90, 0.98, 0.025, 1.50, 'Oak', bev=0.0025, seg=3)
cube('postCollar', 0.450, 0.570, 0.880, 1.000, 1.28, 1.294, 'DarkIron',
     bev=0.0012)
cube('postCap', 0.465, 0.555, 0.895, 0.985, 1.50, 1.516, 'DarkIron',
     bev=0.0012)
cube('hookV', 0.444, 0.462, 0.932, 0.950, 1.516, 1.576, 'DarkIron', bev=0.001)
cube('hookH', 0.404, 0.462, 0.932, 0.950, 1.560, 1.576, 'DarkIron', bev=0.001)
bpy.ops.mesh.primitive_torus_add(major_radius=0.030, minor_radius=0.005,
                                 major_segments=18, minor_segments=8,
                                 location=(0.420, 0.941, 1.532),
                                 rotation=(math.pi / 2, 0, 0))
ring = bpy.context.active_object
ring.name = 'hookRing'
ring.data.materials.append(MATS['DarkIron'])
smooth.add(ring.name)

# ------------------------------------------------- side bench (south arm)
SX0, SX1 = -1.209, 0.43
SN = 4
syw = (-0.62 - (-1.303)) / SN
for i in range(SN):
    y0 = -1.303 + i * syw + 0.002
    y1 = -1.303 + (i + 1) * syw - 0.002
    zj = 0.65 + random.uniform(-0.0006, 0.0006)
    cube('sidePlank%d' % i, SX0, SX1, y0, y1, 0.60, zj, 'Oak')
for lx in (SX0 + 0.05, SX1 - 0.09):
    for ly in (-1.25, -0.75):
        cube('sideLeg', lx, lx + 0.09, ly, ly + 0.09, 0.0, 0.60, 'Oak',
             bev=0.002, seg=3)
for sc in (-1.15, -0.90):
    cube('sideShelf', SX0 + 0.05, SX1 - 0.06, sc - 0.08, sc + 0.08, 0.18, 0.21,
         'Oak')

# ------------------------------------------------- lumber pile (north end)
for (x, r, y0, y1) in ((0.55, 0.056, 0.72, 1.287), (0.72, 0.052, 0.72, 1.287),
                       (0.89, 0.055, 0.72, 1.287)):
    cyl('log1_%d' % int(x * 100), r, y1 - y0, (x, (y0 + y1) / 2,
         TOP1 + r), axis='Y', seg=14)
for (x, r) in ((0.635, 0.049), (0.805, 0.048)):
    cyl('log2_%d' % int(x * 100), r, 0.50, (x, 0.99, 1.055 + r), axis='Y',
        seg=14)
cyl('logOff', 0.040, 0.30, (0.72, 0.88, 1.152 + 0.040), axis='Y', seg=12)

# ------------------------------------------------- on the side bench
build_crate('ammoBig', 0.02, 0.38, -1.26, -1.04, 0.65, 0.16, seed=2)
build_crate('ammoSmall', -0.44, -0.14, -1.24, -1.00, 0.65, 0.13, yaw=0.12,
            seed=3)
# tool roll
cube('rollBase', -0.94, -0.50, -1.20, -0.94, 0.65, 0.662, 'Leather',
     bev=0.0015, seg=3)
for sx in (-0.86, -0.58):
    cube('rollStrap', sx, sx + 0.020, -1.20, -0.94, 0.662, 0.6635, 'Leather',
         bev=0.0008)
cyl('chisel', 0.006, 0.14, (-0.79, -1.03, 0.662 + 0.006), axis='X',
    slot='DarkIron')
cyl('chiselHit', 0.011, 0.065, (-0.6875, -1.03, 0.662 + 0.011), axis='X',
    slot='Oak')
cube('fileBlade', -0.83, -0.61, -1.114, -1.098, 0.662, 0.667, 'DarkIron',
     bev=0.0008)
cyl('fileHit', 0.008, 0.06, (-0.58, -1.106, 0.662 + 0.008), axis='X',
    slot='Oak')
cyl('awl', 0.004, 0.12, (-0.68, -1.17, 0.662 + 0.004), axis='X',
    slot='DarkIron')
cyl('awlHit', 0.008, 0.06, (-0.635, -1.17, 0.662 + 0.008), axis='X', slot='Oak')
# hammer
cyl('hammerHit', 0.013, 0.26, (-0.13, -0.80, 0.65 + 0.013), axis='X',
    slot='Oak')
hb = cube('hammerHead', -0.035, 0.075, -0.823, -0.777, 0.650, 0.696, 'DarkIron',
          bev=0.002, seg=3)
# clay jug
jug = lathe('jug', [
    (0.000, 0.000), (0.028, 0.000), (0.050, 0.004), (0.059, 0.016),
    (0.063, 0.040), (0.063, 0.062), (0.058, 0.086), (0.050, 0.098),
    (0.0485, 0.1025), (0.0512, 0.108), (0.0488, 0.1135), (0.0512, 0.119),
    (0.0490, 0.1245), (0.0440, 0.131), (0.0320, 0.140), (0.0285, 0.149),
    (0.0295, 0.156), (0.0340, 0.161), (0.0350, 0.165), (0.0290, 0.169),
    (0.0190, 0.171), (0.0185, 0.167), (0.000, 0.166)], 40, 'Clay')
place(jug, -1.035, -0.815, 0.65)
sweep('jugHandle', (0.049, 0, 0.099), (0.082, 0, 0.141), (0.030, 0, 0.152),
      0.0042, 10, 'Clay')
place(bpy.data.objects['jugHandle'], -1.035, -0.815, 0.65)

# ---------------------------------------------------------------- bevels
for ob, width, segs in bevels:
    bpy.context.view_layer.objects.active = ob
    m = ob.modifiers.new('B', 'BEVEL')
    m.width = width
    m.segments = segs
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(31)
    bpy.ops.object.modifier_apply(modifier='B')
for ob in bpy.context.scene.objects:
    if ob.type == 'MESH' and ob.name in smooth:
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.shade_smooth()

# ---------------------------------------------------------------- UVs
for ob in bpy.context.scene.objects:
    if ob.type != 'MESH':
        continue
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')

# ------------------------------------------------- vertex dirt (preview only)
for ob in bpy.context.scene.objects:
    if ob.type != 'MESH':
        continue
    ca = ob.data.color_attributes.new('Dirt', 'BYTE_COLOR', 'POINT')
    zs = [v.co.z for v in ob.data.vertices]
    zmin, zmax = min(zs), max(zs)
    jit = [random.random() for _ in ob.data.vertices]
    for k, v in enumerate(ob.data.vertices):
        rel = (v.co.z - zmin) / max(1e-5, zmax - zmin)
        d = max(0.0, min(0.65, 0.5 * (1.0 - rel) ** 1.6 + 0.15 * jit[k]))
        g = int(255 * (1.0 - d))
        ca.data[k].color = (g / 255, g / 255, g / 255, 1.0)
    slot = ob.material_slots[0].material.name if ob.material_slots else ''
    for s in ob.material_slots:
        if not s.material or not s.material.use_nodes:
            continue
        nt = s.material.node_tree
        if nt.nodes.get('DirtHook'):
            continue
        b = nt.nodes['Principled BSDF']
        ca_n = nt.nodes.new('ShaderNodeAttribute')
        ca_n.attribute_name = 'Dirt'
        sep = nt.nodes.new('ShaderNodeSeparateColor')
        mix = nt.nodes.new('ShaderNodeMixRGB')
        mix.name = 'DirtHook'
        mix.inputs['Fac'].default_value = 0.55
        nt.links.new(ca_n.outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Red'], mix.inputs['Color2'])
        if b.inputs['Base Color'].is_linked:
            src = b.inputs['Base Color'].links[0].from_socket
            nt.links.new(src, mix.inputs['Color1'])
            nt.links.new(mix.outputs['Color'], b.inputs['Base Color'])

# ---------------------------------------------------------------- bbox check
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
xs, ys, zs = [], [], []
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        xs.append(w.x); ys.append(w.y); zs.append(w.z)
bbox = (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))
for got, want in zip(bbox[0], BBOX_TARGET[0]):
    assert abs(got - want) < 0.004, 'bbox min mismatch %.4f vs %.4f' % (got, want)
for got, want in zip(bbox[1], BBOX_TARGET[1]):
    assert abs(got - want) < 0.004, 'bbox max mismatch %.4f vs %.4f' % (got, want)
print('BBOX_OK', bbox)

# ---------------------------------------------------------------- preview renders
sc = bpy.context.scene
w = sc.world
w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.85, 0.85, 0.88, 1.0)
bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -0.002))
pvground = bpy.context.active_object
pvground.name = 'pvground'
gm = bpy.data.materials.new('pvground')
gm.use_nodes = True
gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.68, 0.67, 0.63, 1.0)
gm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.95
bpy.context.active_object.data.materials.append(gm)
bpy.ops.object.light_add(type='AREA', location=(1.4, -1.6, 2.2))
k1 = bpy.context.active_object
k1.data.energy = 180; k1.data.size = 2.5
k1.rotation_euler = (math.radians(58), 0, math.radians(40))
bpy.ops.object.light_add(type='AREA', location=(-2.2, 1.2, 1.6))
k2 = bpy.context.active_object
k2.data.energy = 60; k2.data.size = 2.0
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 40
sc.render.resolution_x = 1350
sc.render.resolution_y = 1000
cd = bpy.data.cameras.new('PVCam'); cd.lens = 55
cam = bpy.data.objects.new('PVCam', cd)
sc.collection.objects.link(cam); sc.camera = cam
for name, (loc, look) in {
    'iso': ((-2.6, -2.9, 2.2), (0.0, -0.1, 0.55)),
    'front': ((0.0, -3.8, 1.1), (0.0, 0.0, 0.7)),
    'top': ((0.0, 0.0, 4.2), (0.0, 0.0, 0.0)),
}.items():
    cam.location = loc
    d = Vector(look) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(ROOT, 'preview-%s.png' % name)
    bpy.ops.render.render(write_still=True)
bpy.data.objects.remove(pvground, do_unlink=True)

# ---------------------------------------------------------------- save editable
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(AUTH, 'GunWorkbench_Editable.blend'))

# ---------------------------------------------------------------- join + export
order = {'Oak': 0, 'DarkIron': 1, 'Rope': 2, 'Leather': 3, 'Clay': 4}
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
bpy.ops.object.select_all(action='DESELECT')
ordered = sorted(meshes, key=lambda o: order[o.material_slots[0].material.name])
for o in ordered:
    o.select_set(True)
bpy.context.view_layer.objects.active = ordered[0]
bpy.ops.object.join()
merged = bpy.context.active_object
merged.name = 'SM_GunWorkbench'
slots = [s.material.name for s in merged.material_slots]
tris = sum(len(p.vertices) - 2 for p in merged.data.polygons)
fbx = os.path.join(AUTH, 'SM_GunWorkbench.fbx')
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True,
                         object_types={'MESH'}, axis_forward='-Y', axis_up='Z',
                         mesh_smooth_type='FACE', use_tspace=True,
                         bake_anim=False, add_leaf_bones=False)

manifest = {
    'fbx': fbx,
    'target_dir': '/Game/Building/GunWorkbenchMedieval20260928',
    'slots': slots,
    'bindings': {
        'Oak': '/Game/Props/CastingStation20260926/RealismV5/M_OakDry',
        'DarkIron': '/Game/Props/CastingStation20260926/RealismV5/MI_DarkForgedIron',
        'Rope': '/Game/Dungeons/ArtPass20260922/Materials/MI_Prop_Rope_All',
        'Leather': '/Game/Building/GunWorkbenchMedieval20260928/Materials/M_GWLeather',
        'Clay': '/Game/Building/GunWorkbenchMedieval20260928/Materials/M_GWClay',
    },
    'new_materials': {
        'Leather': ['leather_basecolor.png', 'leather_rough.png', 'leather_normal.png'],
        'Clay': ['clay_basecolor.png', 'clay_rough.png', 'clay_normal.png'],
    },
    'bbox_m': {'min': list(bbox[0]), 'max': list(bbox[1])},
    'triangles': tris,
    'torch_spawn_local_cm': [51.0, 94.0, 136.0],
    'tests_run': False, 'renders_run': True, 'game_started': False,
}
with open(os.path.join(AUTH, 'manifest.json'), 'w', encoding='utf-8') as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
print('MEDIEVAL_WORKBENCH_AUTHORED slots=%s tris=%d' % (slots, tris))
