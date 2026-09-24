"""Author five tier crates (wood -> silver+gems) referencing the current warehouse chest.
Background Blender run; exports one FBX per tier. No renders/tests.

Run:
    & 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b --factory-startup \
      --python-exit-code 1 --python SourceAssets/WarehouseCrateTiers20260924/author_crates.py
"""
import bpy, bmesh, json, math
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / 'Authored'; OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'; scene.unit_settings.scale_length = .01

# Shared footprint of the current warehouse chest (~150 x 120 x 120 cm), front = -Y, ground pivot.
W, D = 150., 120.
HX, HY = W / 2, D / 2          # 75, 60
BODY_TOP = 64.
ARCH_RY, ARCH_HZ = 62., 46.    # lid outer arch about z=BODY_TOP
LID_X = 78.                    # lid half length (overhang)

SLOT_ORDER = ['Crate_Wood', 'Crate_WoodDark', 'Crate_Stone', 'Crate_Iron',
              'Crate_IronDark', 'Crate_Gold', 'Crate_Silver', 'Crate_Gem']
SLOT_BASE = {  # linear albedo, metallic, roughness (blend-side preview only; UE materials authored in installer)
    'Crate_Wood':     (.28, .155, .075, 0, .62),
    'Crate_WoodDark': (.155, .085, .042, 0, .66),
    'Crate_Stone':    (.21, .205, .195, 0, .88),
    'Crate_Iron':     (.42, .425, .45, 1, .42),
    'Crate_IronDark': (.055, .058, .062, .9, .55),
    'Crate_Gold':     (.62, .40, .12, 1, .30),
    'Crate_Silver':   (.58, .59, .62, 1, .22),
    'Crate_Gem':      (.02, .12, .55, 0, .06),
}
mats = {}
for name in SLOT_ORDER:
    m = bpy.data.materials.new(name); m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    r, g, b, metal, rough = SLOT_BASE[name]
    bsdf.inputs['Base Color'].default_value = (r, g, b, 1)
    bsdf.inputs['Metallic'].default_value = metal
    bsdf.inputs['Roughness'].default_value = rough
    if name == 'Crate_Gem':
        bsdf.inputs['Coat Weight'].default_value = 1.0
    mats[name] = m

def solo(obj):
    bpy.context.view_layer.objects.active = obj
    for sel in list(bpy.context.selected_objects): sel.select_set(False)
    obj.select_set(True)

def finish(obj, mat, bevel=0, smooth=False):
    obj.data.materials.clear(); obj.data.materials.append(mats[mat])
    solo(obj)
    if bevel:
        mod = obj.modifiers.new('MachinedEdges', 'BEVEL'); mod.width = bevel; mod.segments = 2
        mod.limit_method = 'ANGLE'; mod.angle_limit = math.radians(35); mod.use_clamp_overlap = True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for face in obj.data.polygons: face.use_smooth = smooth
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return obj

def box(name, loc, size, mat, bevel=1.2):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object; obj.dimensions = size
    return finish(obj, mat, bevel)

def cylinder(name, loc, radius, depth, mat, axis='Z', bevel=.4, smooth=True, verts=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc)
    obj = bpy.context.object
    if axis == 'X': obj.rotation_euler.y = math.pi / 2
    if axis == 'Y': obj.rotation_euler.x = math.pi / 2
    return finish(obj, mat, bevel, smooth)

def sphere(name, loc, radius, mat, scale=(1, 1, 1), seg=16, ring=10):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=ring, radius=radius, location=loc)
    obj = bpy.context.object; obj.scale = scale
    return finish(obj, mat, 0, True)

def arch_shell(name, x0, x1, ry_o, h_o, ry_i, h_i, mat, z_base=BODY_TOP, n=32, cap_ends=True, smooth=True):
    """Closed-thickness barrel vault segment; open underside unless cap_ends."""
    verts = []
    for x in (x0, x1):
        for r, h in ((ry_o, h_o), (ry_i, h_i)):
            verts.extend((x, -r * math.cos(i * math.pi / n), z_base + h * math.sin(i * math.pi / n)) for i in range(n + 1))
    def v(side, inner, i): return (side * 2 + inner) * (n + 1) + i
    faces = []
    for i in range(n):
        faces += [(v(0, 0, i), v(1, 0, i), v(1, 0, i + 1), v(0, 0, i + 1)),
                  (v(0, 1, i + 1), v(1, 1, i + 1), v(1, 1, i), v(0, 1, i))]
        for side in (0, 1):
            faces.append((v(side, 0, i), v(side, 0, i + 1), v(side, 1, i + 1), v(side, 1, i)))
    if cap_ends:
        for i in (0, n):
            faces.append((v(0, 0, i), v(1, 0, i), v(1, 1, i), v(0, 1, i)))
    data = bpy.data.meshes.new(name); data.from_pydata(verts, [], faces)
    bm = bmesh.new(); bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces)); bm.to_mesh(data); bm.free()
    obj = bpy.data.objects.new(name, data); scene.collection.objects.link(obj)
    return finish(obj, mat, 0, smooth)

def curve(name, points, radius, mat):
    data = bpy.data.curves.new(name, 'CURVE'); data.dimensions = '3D'
    data.resolution_u = 6; data.bevel_depth = radius; data.bevel_resolution = 2; data.use_fill_caps = True
    spline = data.splines.new('BEZIER'); spline.bezier_points.add(len(points) - 1)
    for p, co in zip(spline.bezier_points, points):
        p.co = co; p.handle_left_type = 'AUTO'; p.handle_right_type = 'AUTO'
    obj = bpy.data.objects.new(name, data); scene.collection.objects.link(obj)
    solo(obj)
    bpy.ops.object.convert(target='MESH')
    obj = bpy.context.object
    # Blender 5.1 headless ignores use_fill_caps on convert; close end loops explicitly.
    bm = bmesh.new(); bm.from_mesh(obj.data)
    for _ in range(8):
        boundary_edges = [e for e in bm.edges if e.is_boundary]
        if not boundary_edges: break
        e0 = boundary_edges[0]
        loop = [e0.verts[0], e0.verts[1]]
        cur, nxt = e0, e0.verts[1]
        while True:
            cands = [le for le in nxt.link_edges if le.is_boundary and le != cur]
            if not cands: break
            cur = cands[0]; nxt = cur.other_vert(nxt)
            if nxt == loop[0]: break
            loop.append(nxt)
        if len(loop) < 3: break
        bm.faces.new(loop)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data); bm.free()
    return finish(obj, mat, 0, True)

# ----------------------------------------------------------------------------- shared builders
def feet(mat):
    return [box('Foot_%s_%s' % (sx, sy), (sx * 58, sy * 44, 4), (18, 18, 8), mat, bevel=2)
            for sx in (-1, 1) for sy in (-1, 1)]

def bottom_rail(mat):
    return [box('Rail_Bottom_Front', (0, -HY + 2, 12), (W + 6, 8, 8), mat, bevel=1.4),
            box('Rail_Bottom_Back', (0, HY - 2, 12), (W + 6, 8, 8), mat, bevel=1.4),
            box('Rail_Bottom_Left', (-HX + 1, 0, 12), (8, D - 8, 8), mat, bevel=1.4),
            box('Rail_Bottom_Right', (HX - 1, 0, 12), (8, D - 8, 8), mat, bevel=1.4)]

def top_rail(mat):
    return [box('Rail_Top_Front', (0, -HY - 1, BODY_TOP - 4), (W + 10, 10, 8), mat, bevel=1.4),
            box('Rail_Top_Back', (0, HY + 1, BODY_TOP - 4), (W + 10, 10, 8), mat, bevel=1.4),
            box('Rail_Top_Left', (-HX - 2, 0, BODY_TOP - 4), (10, D + 2, 8), mat, bevel=1.4),
            box('Rail_Top_Right', (HX + 2, 0, BODY_TOP - 4), (10, D + 2, 8), mat, bevel=1.4)]

def corner_posts(mat, size=10):
    return [box('Corner_%s_%s' % (sx, sy), (sx * (HX - 2), sy * (HY - 2), 36), (size, size, 52), mat, bevel=1.6)
            for sx in (-1, 1) for sy in (-1, 1)]

def plank_walls(plank_mat, core_mat):
    out = []
    rows = 4; gap = 1.6
    h = (BODY_TOP - 12 - rows * gap) / rows
    for r in range(rows):
        cz = 12 + gap + r * (h + gap) + h / 2
        for sy in (-1, 1):
            out.append(box('Plank_FB_%s_%s' % (sy, r), (0, sy * (HY - 3), cz), (W - 14, 6, h), plank_mat, bevel=.8))
            out.append(box('Core_FB_%s' % sy, (0, sy * (HY - 7), 37), (W - 16, 3, BODY_TOP - 14), core_mat, bevel=0))
        for sx in (-1, 1):
            out.append(box('Plank_LR_%s_%s' % (sx, r), (sx * (HX - 3), 0, cz), (6, D - 14, h), plank_mat, bevel=.8))
            out.append(box('Core_LR_%s' % sx, (sx * (HX - 7), 0, 37), (3, D - 16, BODY_TOP - 14), core_mat, bevel=0))
    return out

def solid_walls(mat):
    return [box('Wall_FB_%s' % sy, (0, sy * (HY - 3), 37), (W - 8, 6, BODY_TOP - 12), mat, bevel=1) for sy in (-1, 1)] + \
           [box('Wall_LR_%s' % sx, (sx * (HX - 3), 0, 37), (6, D - 8, BODY_TOP - 12), mat, bevel=1) for sx in (-1, 1)]

def seam_strips(mat):
    out = []
    for r in (1, 2, 3):
        cz = 12 + r * ((BODY_TOP - 12) / 4)
        for sy in (-1, 1):
            out.append(box('Seam_FB_%s_%s' % (sy, r), (0, sy * (HY + .4), cz), (W - 10, 1.6, 1.4), mat, bevel=0))
        for sx in (-1, 1):
            out.append(box('Seam_LR_%s_%s' % (sx, r), (sx * (HX + .4), 0, cz), (1.6, D - 10, 1.4), mat, bevel=0))
    return out

def wall_rivets(mat):
    out = []
    for r in (1, 2, 3):
        cz = 12 + r * ((BODY_TOP - 12) / 4)
        for x in (-60, -30, 0, 30, 60):
            for sy in (-1, 1):
                out.append(sphere('WallRivet_FB_%s_%s' % (x, sy), (x, sy * HY, cz), 1.35, mat, scale=(1, .55, 1)))
        for y in (-44, 0, 44):
            for sx in (-1, 1):
                out.append(sphere('WallRivet_LR_%s_%s' % (y, sx), (sx * HX, y, cz), 1.35, mat, scale=(.55, 1, 1)))
    return out

def lid_shell(mat, planks=False, dark_mat=None):
    if not planks:
        return [arch_shell('Lid_Vault', -LID_X, LID_X, ARCH_RY, ARCH_HZ, ARCH_RY - 4.5, ARCH_HZ - 4.5, mat, n=36)]
    out = [arch_shell('Lid_Under', -LID_X, LID_X, ARCH_RY - 1.6, ARCH_HZ - 1.6, ARCH_RY - 3.4, ARCH_HZ - 3.4, dark_mat, n=36)]
    xs = [(-LID_X, -LID_X + 26), (-46, -19), (-12, 12), (19, 46), (LID_X - 26, LID_X)]
    for i, (a, b) in enumerate(xs):
        out.append(arch_shell('Lid_Plank_%s' % i, a, b, ARCH_RY, ARCH_HZ, ARCH_RY - 2.6, ARCH_HZ - 2.6, mat, n=24))
    return out

def lid_bands(mat, rivet_mat=None, positions=(-52, 0, 52)):
    out = []
    for i, x in enumerate(positions):
        out.append(arch_shell('Lid_Band_%s' % i, x - 4.5, x + 4.5, ARCH_RY + 1.3, ARCH_HZ + 1.3, ARCH_RY - .8, ARCH_HZ - .8, mat, n=28, cap_ends=True))
        if rivet_mat is not None:
            for deg in (18, 45, 72, 108, 135, 162):
                t = math.radians(deg)
                out.append(sphere('LidBandRivet_%s_%s' % (i, deg),
                                  (x, -(ARCH_RY + 1.4) * math.cos(t), BODY_TOP + (ARCH_HZ + 1.4) * math.sin(t)),
                                  1.15, rivet_mat))
    return out

def lid_cross_battens(mat, positions=(-49, -15.5, 15.5, 49)):
    return [arch_shell('Lid_Batten_%s' % i, x - 5.5, x + 5.5, ARCH_RY + 1.1, ARCH_HZ + 1.1, ARCH_RY - .6, ARCH_HZ - .6, mat, n=24, cap_ends=True)
            for i, x in enumerate(positions)]

def lock_strap(strap_mat, plate_mat, pin_mat):
    return [box('Lock_Strap', (0, -61.5, 78), (11, 5, 26), strap_mat, bevel=1.6),
            box('Lock_Plate', (0, -61.5, 46), (15, 4, 34), plate_mat, bevel=2),
            cylinder('Lock_Eye', (0, -64.5, 52), 4.6, 4, pin_mat, axis='Y', bevel=.3),
            box('Lock_Shackle', (0, -64.5, 58), (6, 4, 10), pin_mat, bevel=1.2)]

def hinges(mat):
    out = []
    for x in (-42, 42):
        out.append(cylinder('Hinge_%s' % x, (x, HY + 2.5, BODY_TOP + 2), 3.4, 20, mat, axis='X', bevel=.5))
        out.append(box('HingePlate_%s' % x, (x, HY + .5, BODY_TOP - 6), (16, 4, 12), mat, bevel=.8))
    return out

def medallion(prefix, loc, radius, ring_mat, inset_mat, axis='Y', ticks=20, gem_mat=None):
    cx, cy, cz = loc
    out = []
    if axis == 'Y':
        front = -1
        out.append(cylinder(prefix + '_Disc', (cx, cy, cz), radius, 3, ring_mat, axis='Y', bevel=.6))
        out.append(cylinder(prefix + '_Inset', (cx, cy + front * 1.9, cz), radius * .62, 1.6, inset_mat, axis='Y', bevel=.2))
        for i in range(ticks):
            a = 2 * math.pi * i / ticks
            tick = box(prefix + '_Tick_%s' % i, (cx + math.cos(a) * radius * .8, cy + front * 1.6, cz + math.sin(a) * radius * .8),
                       (1.5, 1.2, 3.4), inset_mat, bevel=0)
            tick.rotation_euler.y = -a
            out.append(tick)
        if gem_mat:
            out.append(sphere(prefix + '_Gem', (cx, cy - 2.6, cz), radius * .34, gem_mat, scale=(1, .55, 1), seg=20, ring=12))
    else:
        front = 1 if cx > 0 else -1
        out.append(cylinder(prefix + '_Disc', (cx, cy, cz), radius, 3, ring_mat, axis='X', bevel=.6))
        out.append(cylinder(prefix + '_Inset', (cx + front * 1.9, cy, cz), radius * .62, 1.6, inset_mat, axis='X', bevel=.2))
        for i in range(ticks):
            a = 2 * math.pi * i / ticks
            tick = box(prefix + '_Tick_%s' % i, (cx + front * 1.6, cy + math.cos(a) * radius * .8, cz + math.sin(a) * radius * .8),
                       (1.2, 1.5, 3.4), inset_mat, bevel=0)
            tick.rotation_euler.x = a
            out.append(tick)
        if gem_mat:
            out.append(sphere(prefix + '_Gem', (cx + front * 2.6, cy, cz), radius * .34, gem_mat, scale=(.55, 1, 1), seg=20, ring=12))
    return out

def scrollwork(prefix, plane, sign, mat, scale=1.):
    # First and last points sink into the panel so tube end caps are never exposed.
    if plane == 'Y':
        pts = [(sign * 22 * scale, -HY + 2., 34), (sign * 38 * scale, -HY - 1.2, 46),
               (sign * 58 * scale, -HY - 1.2, 44), (sign * 66 * scale, -HY - 1.2, 30),
               (sign * 54 * scale, -HY - 1.2, 24), (sign * 42 * scale, -HY + 2., 30)]
    else:
        pts = [(sign * (HX - 2.), -26 * scale, 30), (sign * (HX + 1.2), -8 * scale, 42),
               (sign * (HX + 1.2), 14 * scale, 44), (sign * (HX + 1.2), 30 * scale, 34),
               (sign * (HX + 1.2), 16 * scale, 24), (sign * (HX - 2.), 2 * scale, 30)]
    return [curve(prefix, pts, 1.35 * scale, mat)]

def panel_frame(prefix, mat):
    """Rectangular gold trim outline inset on the front panel face."""
    t, w_, h_ = 1.6, 52., 34.
    return [box(prefix + '_H1', (0, -HY - .8, 52), (w_ * 2, 2.2, t), mat, bevel=.4),
            box(prefix + '_H2', (0, -HY - .8, 52 - h_), (w_ * 2, 2.2, t), mat, bevel=.4),
            box(prefix + '_V1', (-w_, -HY - .8, 52 - h_ / 2), (t, 2.2, h_), mat, bevel=.4),
            box(prefix + '_V2', (w_, -HY - .8, 52 - h_ / 2), (t, 2.2, h_), mat, bevel=.4)]

def front_gem_studs(mat):
    return [sphere('GemStud_%s' % s, (s * 32, -61.2, 46), 4.2, mat, scale=(1, .5, 1), seg=20, ring=12) for s in (-1, 1)]

def lid_apex_gem(mat):
    return [sphere('LidApexGem', (0, 0, BODY_TOP + ARCH_HZ + 2.6), 5.4, mat, scale=(1.6, 1, .8), seg=20, ring=12),
            arch_shell('ApexRing', -8, 8, ARCH_RY + 1.0, ARCH_HZ + 1.0, ARCH_RY - 2.0, ARCH_HZ - 2.0, 'Crate_Gold', n=12, cap_ends=True)]

def corner_trim(mat):
    return [box('CornerTrim_%s_%s' % (sx, sy), (sx * (HX - 2), sy * (HY - 2), 36), (12.6, 12.6, 48), mat, bevel=.8)
            for sx in (-1, 1) for sy in (-1, 1)]

# ----------------------------------------------------------------------------- tier recipes
def build_tier(tier):
    parts = []
    if tier == 1:
        parts += feet('Crate_WoodDark') + bottom_rail('Crate_WoodDark') + top_rail('Crate_WoodDark')
        parts += corner_posts('Crate_WoodDark', size=9)
        parts += plank_walls('Crate_Wood', 'Crate_WoodDark')
        parts += lid_shell('Crate_Wood', planks=True, dark_mat='Crate_WoodDark')
        parts += lid_cross_battens('Crate_WoodDark')
        parts += lock_strap('Crate_WoodDark', 'Crate_IronDark', 'Crate_IronDark')
        parts += hinges('Crate_IronDark')
        for y in (-HY - 1, HY + 1):
            for x in (-60, -30, 0, 30, 60):
                parts.append(sphere('Nail_Top_%s_%s' % (x, y), (x, y, BODY_TOP - .2), 1.0, 'Crate_IronDark', scale=(1, 1, .5), seg=10, ring=6))
                parts.append(sphere('Nail_Bottom_%s_%s' % (x, y), (x, y, 16.4), 1.0, 'Crate_IronDark', scale=(1, 1, .5), seg=10, ring=6))
    elif tier == 2:
        parts += feet('Crate_Stone') + bottom_rail('Crate_Stone') + top_rail('Crate_Stone')
        parts += corner_posts('Crate_Stone', size=12)
        parts += plank_walls('Crate_Wood', 'Crate_Stone')
        parts += lid_shell('Crate_Wood', planks=True, dark_mat='Crate_Stone')
        parts += lid_bands('Crate_Stone')
        parts += lock_strap('Crate_Iron', 'Crate_Iron', 'Crate_IronDark')
        parts += hinges('Crate_Iron')
        parts += [box('StoneCap_%s_%s' % (sx, sy), (sx * (HX - 2), sy * (HY - 2), BODY_TOP + 2), (14, 14, 8), 'Crate_Stone', bevel=1.8)
                  for sx in (-1, 1) for sy in (-1, 1)]
    elif tier == 3:
        parts += feet('Crate_Iron') + bottom_rail('Crate_Iron') + top_rail('Crate_Iron')
        parts += corner_posts('Crate_Iron', size=12)
        parts += solid_walls('Crate_Iron')
        parts += seam_strips('Crate_IronDark') + wall_rivets('Crate_Iron')
        parts += lid_shell('Crate_Iron')
        parts += lid_bands('Crate_Iron', rivet_mat='Crate_Iron')
        parts += lock_strap('Crate_Iron', 'Crate_IronDark', 'Crate_Iron')
        parts += hinges('Crate_Iron')
        parts += medallion('Badge_Front', (0, -HY - .5, 40), 13, 'Crate_Iron', 'Crate_IronDark')
        parts += medallion('Badge_L', (-HX - .5, 0, 40), 11, 'Crate_Iron', 'Crate_IronDark', axis='X')
        parts += medallion('Badge_R', (HX + .5, 0, 40), 11, 'Crate_Iron', 'Crate_IronDark', axis='X')
    elif tier == 4:
        parts += feet('Crate_Iron') + bottom_rail('Crate_Iron') + top_rail('Crate_Gold')
        parts += corner_posts('Crate_Iron', size=12) + corner_trim('Crate_Gold')
        parts += solid_walls('Crate_Iron')
        parts += seam_strips('Crate_IronDark') + wall_rivets('Crate_Iron')
        parts += lid_shell('Crate_Iron')
        parts += lid_bands('Crate_Gold', rivet_mat='Crate_Gold')
        parts += lock_strap('Crate_Gold', 'Crate_Gold', 'Crate_IronDark')
        parts += hinges('Crate_Gold')
        parts += medallion('Badge_Front', (0, -HY - .5, 40), 13, 'Crate_Gold', 'Crate_IronDark')
        parts += medallion('Badge_L', (-HX - .5, 0, 40), 11, 'Crate_Gold', 'Crate_IronDark', axis='X')
        parts += medallion('Badge_R', (HX + .5, 0, 40), 11, 'Crate_Gold', 'Crate_IronDark', axis='X')
        for sign in (-1, 1):
            parts += scrollwork('Scroll_F_%s' % sign, 'Y', sign, 'Crate_Gold')
            parts += scrollwork('Scroll_L_%s' % sign, 'X', sign, 'Crate_Gold', scale=.82)
        parts += panel_frame('Frame_Front', 'Crate_Gold')
    elif tier == 5:
        parts += feet('Crate_Silver') + bottom_rail('Crate_Gold') + top_rail('Crate_Gold')
        parts += corner_posts('Crate_Silver', size=12) + corner_trim('Crate_Gold')
        parts += solid_walls('Crate_Silver')
        parts += seam_strips('Crate_Gold') + wall_rivets('Crate_Gold')
        parts += lid_shell('Crate_Silver')
        parts += lid_bands('Crate_Gold', rivet_mat='Crate_Gold')
        parts += lock_strap('Crate_Gold', 'Crate_Gold', 'Crate_Silver')
        parts += hinges('Crate_Gold')
        parts += medallion('Badge_Front', (0, -HY - .5, 40), 14, 'Crate_Gold', 'Crate_Silver', gem_mat='Crate_Gem')
        parts += medallion('Badge_L', (-HX - .5, 0, 40), 12, 'Crate_Gold', 'Crate_Silver', axis='X', gem_mat='Crate_Gem')
        parts += medallion('Badge_R', (HX + .5, 0, 40), 12, 'Crate_Gold', 'Crate_Silver', axis='X', gem_mat='Crate_Gem')
        for sign in (-1, 1):
            parts += scrollwork('Scroll_F_%s' % sign, 'Y', sign, 'Crate_Gold')
            parts += scrollwork('Scroll_L_%s' % sign, 'X', sign, 'Crate_Gold', scale=.82)
        parts += panel_frame('Frame_Front', 'Crate_Gold')
        parts += front_gem_studs('Crate_Gem') + lid_apex_gem('Crate_Gem')
    return parts

TIERS = {
    1: 'SM_WarehouseCrate_T1_Wood',
    2: 'SM_WarehouseCrate_T2_StoneWood',
    3: 'SM_WarehouseCrate_T3_Iron',
    4: 'SM_WarehouseCrate_T4_IronGold',
    5: 'SM_WarehouseCrate_T5_SilverGem',
}

def planar_uv(mesh_obj):
    uv = mesh_obj.data.uv_layers.new(name='UV0_Physical')
    me = mesh_obj.data
    for face in me.polygons:
        axis = max(range(3), key=lambda i: abs(face.normal[i]))
        for index in face.loop_indices:
            p = me.vertices[me.loops[index].vertex_index].co / 100
            uv.data[index].uv = (p.y, p.z) if axis == 0 else (p.x, p.z) if axis == 1 else (p.x, p.y)

authoring = {'unit': 'cm', 'front': '-Y', 'reference': 'warehouse chest RitualV8 ~150x120x120cm', 'tiers': {}}
for tier, name in TIERS.items():
    parts = build_tier(tier)
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    mesh = bpy.context.object; mesh.name = name
    old = [m.name for m in mesh.data.materials]
    orig = [poly.material_index for poly in mesh.data.polygons]  # capture BEFORE clear() clamps them
    order = [s for s in SLOT_ORDER if s in old]
    remap = {i: order.index(old[i]) for i in range(len(old))}
    mesh.data.materials.clear()
    for s in order: mesh.data.materials.append(mats[s])
    for poly, mi in zip(mesh.data.polygons, orig): poly.material_index = remap[mi]
    planar_uv(mesh)
    tri = mesh.modifiers.new('ExportTriangles', 'TRIANGULATE')
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.modifier_apply(modifier=tri.name)
    # topology sanity: c==1 open hole edges, c>=3 non-manifold (self-intersecting decoration tubes)
    edge_count = {}
    for poly in mesh.data.polygons:
        for e in poly.edge_keys: edge_count[e] = edge_count.get(e, 0) + 1
    holes = sum(1 for c in edge_count.values() if c == 1)
    nonmanifold = sum(1 for c in edge_count.values() if c >= 3)
    bpy.ops.object.select_all(action='DESELECT'); mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.export_scene.fbx(filepath=str(OUT / (name + '.fbx')), use_selection=True, object_types={'MESH'},
        apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Y', axis_up='Z',
        mesh_smooth_type='FACE', bake_anim=False)
    slot_polys = {}
    for poly in mesh.data.polygons: slot_polys[poly.material_index] = slot_polys.get(poly.material_index, 0) + 1
    authoring['tiers'][name] = {'slots': [[m.name, slot_polys.get(i, 0)] for i, m in enumerate(mesh.data.materials)],
                                'tris': len(mesh.data.polygons),
                                'dims_cm': [round(v, 1) for v in mesh.dimensions],
                                'open_hole_edges': holes, 'nonmanifold_edges': nonmanifold}
    print('CRATE_AUTHORED ' + name + ' ' + json.dumps(authoring['tiers'][name]))
    if holes:
        print('CRATE_HOLE_WARNING ' + name + ' open_hole_edges=' + str(holes))

bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'WarehouseCrateTiers.blend'))
authoring['rendered'] = False; authoring['tested'] = False
(HERE / 'authoring.json').write_text(json.dumps(authoring, indent=2), encoding='utf-8')
print('CRATES_AUTHORED ' + str(len(TIERS)))
