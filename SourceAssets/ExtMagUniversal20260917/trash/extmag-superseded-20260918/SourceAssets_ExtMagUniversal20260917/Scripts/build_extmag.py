"""Author the universal extended magazine (SM_ExtMag_Universal).

Frame: origin = throat top-face centre; +Z out of the well; +Y toward the
muzzle once mounted; +X right. Blender metres (same numbers as the metre-
valued WPN_root bone frame used by the runtime mounts).

The script builds the mesh with bmesh, renders composite previews with each
rifle placed at its per-gun seat, and writes seat_constants.json with the
WPN_root-relative transforms for the C++ side.

Run: blender -b -P build_extmag.py [-- export]
"""
import bpy
import bmesh
import json
import math
import os
import sys
from mathutils import Matrix, Vector, Quaternion as BQuat

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
REF = os.path.join(ROOT, "Reference")
OUT = os.path.join(ROOT, "FBX")
SA = r"D:\FPS3D\FPSGAME\SourceAssets"

GUNS = {
    "M4": os.path.join(SA, r"M4HK416Replica20260910\SK_M4_FoldingSights_HK416.fbx"),
    "AKM": os.path.join(SA, r"AKMSoviet20260911\SK_AKM_MannyNative.fbx"),
    "QBZ": os.path.join(SA, r"QBZ191MagazineSeat20260913\SK_QBZ191_Manny.fbx"),
}

# ---- design parameters (metres) ------------------------------------------
THROAT_W = 0.0210      # x width at the throat
THROAT_D = 0.0300      # y depth at the throat
THROAT_LEN = 0.038     # straight insert section below the seat plane
BODY_W = 0.0255
BODY_D = 0.0350
TRANS_LEN = 0.018      # throat -> body transition length
STRAIGHT_LEN = 0.020   # straight body section after the transition
CURVE_TURN = math.radians(32)   # total forward curve
CURVE_R = 0.215
BASE_LEN = 0.011       # baseplate height along the local axis
BASE_OVERH = 0.0022    # baseplate overhang per side
RING_STEP = 0.004
CORNER_SEGS = 3        # per corner of the rounded rect
BEVEL_W = 0.0006
RIBS = 7               # shallow side grooves below the transition
RIB_DEPTH = 0.0005
RIB_LEN = 0.004
WINDOWS = 4            # witness windows on the left face
WIN_W = 0.006          # along the mag axis
WIN_H = 0.0035         # across the face
WIN_START = 0.060      # below the seat plane
WIN_STEP = 0.019

# ---- per-gun seats: (x, y, z) of the throat-top centre + rake -------------
SEATS = {
    "M4": {"loc": (0.058, 0.257, -0.070), "rake_deg": 15.0},
    "AKM": {"loc": (0.062, 0.243, -0.105), "rake_deg": 20.0},
    "QBZ": {"loc": (0.054, 0.260, -0.056), "rake_deg": 13.0},
}

EXPORT = True


def rounded_rect(w, d, r, segs):
    """Ring of Vector-local (x, y) points centred at origin."""
    r = min(r, w * 0.5, d * 0.5)
    pts = []
    corners = [
        (w * 0.5 - r, d * 0.5 - r, 0.0),
        (-(w * 0.5 - r), d * 0.5 - r, math.pi * 0.5),
        (-(w * 0.5 - r), -(d * 0.5 - r), math.pi),
        (w * 0.5 - r, -(d * 0.5 - r), math.pi * 1.5),
    ]
    for cx, cy, a0 in corners:
        for i in range(segs + 1):
            a = a0 + (math.pi * 0.5) * i / segs
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    # de-duplicate the seam points per corner
    out = [pts[0]]
    for p in pts[1:]:
        if (p[0] - out[-1][0]) ** 2 + (p[1] - out[-1][1]) ** 2 > 1e-12:
            out.append(p)
    return out


def path_frame(s_total, straight_end):
    """Centreline point + tangent tilt (rad from straight down) at arc length
    s measured down from the seat plane. The arc starts with a vertical
    tangent and bends forward: y = R(1-cos a), z = -start - R sin a."""
    curve_start = straight_end
    larc = CURVE_TURN * CURVE_R
    if s_total <= curve_start:
        return Vector((0, 0, -s_total)), 0.0
    t = min(s_total - curve_start, larc)
    ang = t / CURVE_R
    y = CURVE_R * (1.0 - math.cos(ang))
    z = -curve_start - CURVE_R * math.sin(ang)
    if s_total > curve_start + larc:
        extra = s_total - (curve_start + larc)
        y += math.sin(CURVE_TURN) * extra
        z -= math.cos(CURVE_TURN) * extra
        ang = CURVE_TURN
    return Vector((0, y, z)), ang


def cross_dims(s, straight_end):
    """Width/depth at arc length s."""
    if s <= THROAT_LEN:
        t = s / THROAT_LEN
        w = THROAT_W + (BODY_W - THROAT_W) * t
        d = THROAT_D + (BODY_D - THROAT_D) * t
    else:
        w, d = BODY_W, BODY_D
    return w, d


def build_mag():
    bm = bmesh.new()
    straight_end = THROAT_LEN + TRANS_LEN + STRAIGHT_LEN
    total = straight_end + CURVE_TURN * CURVE_R
    ring_prot = rounded_rect(1, 1, 0.3, CORNER_SEGS)
    stations = []
    s = 0.0
    while s < total:
        stations.append(s)
        s += RING_STEP
    stations.append(total)
    rings = []
    for i, sval in enumerate(stations):
        pos, ang = path_frame(sval, straight_end)
        w, d = cross_dims(sval, straight_end)
        ring = []
        cos_a, sin_a = math.cos(ang), math.sin(ang)
        for (lx, ly) in ring_prot:
            # ring_prot spans +-0.5 for unit size; scale directly to w/d
            px = lx * w
            py = ly * d
            y = pos.y + py * cos_a
            z = pos.z + py * sin_a
            ring.append(bm.verts.new((px, y, z)))
        rings.append(ring)
    for a, b in zip(rings[:-1], rings[1:]):
        n = len(a)
        for i in range(n):
            bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    # caps
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])

    # baseplate: short continuation with overhang
    pos, ang = path_frame(total, straight_end)
    cos_a, sin_a = math.cos(ang), math.sin(ang)
    plate = []
    prot = rounded_rect(1, 1, 0.3, CORNER_SEGS)
    for k, depth in enumerate((BASE_LEN * 0.35, BASE_LEN)):
        w = BODY_W + BASE_OVERH * 2
        d = BODY_D + BASE_OVERH * 2
        ring = []
        for (lx, ly) in prot:
            px = lx * w
            py = ly * d
            y = pos.y + py * cos_a - (depth) * sin_a
            z = pos.z + py * sin_a - (depth) * cos_a
            ring.append(bm.verts.new((px, y, z)))
        plate.append(ring)
    for a, b in zip(plate[:-1], plate[1:]):
        n = len(a)
        for i in range(n):
            bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    n = len(plate[-1])
    for i in range(n):
        bm.faces.new((plate[0][(i + 1) % n], plate[0][i], rings[-1][i], rings[-1][(i + 1) % n]))
    bm.faces.new(plate[-1][::-1])

    me = bpy.data.meshes.new("SM_ExtMag_Universal")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("SM_ExtMag_Universal", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob, straight_end, total


def add_details(ob, straight_end, total):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    # side grooves: pinch ring verts inward on the x extremes within rib bands
    for k in range(RIBS):
        band_c = THROAT_LEN + TRANS_LEN + 0.012 + k * 0.016
        if band_c > total - BASE_LEN - 0.02:
            break
        cpos, _ = path_frame(band_c, straight_end)
        for v in bm.verts:
            if abs(v.co.x) > BODY_W * 0.30:
                dy = v.co.y - cpos.y
                dz = v.co.z - cpos.z
                if dy * dy + dz * dz < (RIB_LEN * 0.5) ** 2:
                    v.co.x -= (1.0 if v.co.x > 0 else -1.0) * RIB_DEPTH

    # witness windows on the left face: boolean cutters
    bpy.ops.object.select_all(action='DESELECT')
    for k in range(WINDOWS):
        s_c = WIN_START + k * WIN_STEP
        if s_c > total - BASE_LEN - 0.02:
            break
        pos, ang = path_frame(s_c, straight_end)
        cos_a, sin_a = math.cos(ang), math.sin(ang)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
        cut = bpy.context.object
        cut.name = f"cutter{k}"
        cut.scale = (0.02, WIN_H, WIN_W)
        # centre of the left face at this station, tilted with the mag
        face_y = pos.y - BODY_D * 0.5 * cos_a
        face_z = pos.z - BODY_D * 0.5 * sin_a
        cut.location = (-BODY_W * 0.5, face_y, face_z)
        cut.rotation_euler = (ang, 0, 0)
        bpy.ops.object.transform_apply(scale=True)
    # sequential boolean difference
    me = ob.data
    for obj in list(bpy.data.objects):
        if obj.name.startswith("cutter"):
            mod = ob.modifiers.new("cut", 'BOOLEAN')
            mod.object = obj
            mod.operation = 'DIFFERENCE'
            bpy.context.view_layer.objects.active = ob
            bpy.ops.object.modifier_apply(modifier=mod.name)
            bpy.data.objects.remove(obj, do_unlink=True)

    # bevel everything lightly
    be = ob.modifiers.new("bevel", 'BEVEL')
    be.width = BEVEL_W
    be.segments = 2
    be.limit_method = 'ANGLE'
    be.angle_limit = math.radians(50)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=be.name)

    # materials: 0 polymer body, 1 metal baseplate
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    plate_start_z = None
    pos, ang = path_frame(total, straight_end)
    for f in bm.faces:
        c = f.calc_center_median()
        # distance along the mag axis beyond 'total' belongs to the plate
        s_axis = -c.z / max(math.cos(ang), 1e-6) if abs(ang) < 0.1 else None
        # approximate: plate = verts below the arc end station
        _, ang2 = path_frame(total, straight_end)
        end_pos, _ = path_frame(total, straight_end)
        if c.z < end_pos.z - 0.001:
            f.material_index = 1
        else:
            f.material_index = 0
    bm.to_mesh(me)
    bm.free()

    m_poly = bpy.data.materials.new("M_ExtMag_Polymer")
    m_poly.use_nodes = True
    b = m_poly.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.035, 0.036, 0.040, 1)
    b.inputs["Roughness"].default_value = 0.52
    m_metal = bpy.data.materials.new("M_ExtMag_Metal")
    m_metal.use_nodes = True
    b = m_metal.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.10, 0.10, 0.11, 1)
    b.inputs["Metallic"].default_value = 0.9
    b.inputs["Roughness"].default_value = 0.4
    me.materials.append(m_poly)
    me.materials.append(m_metal)

    # UV: cube project from three views (simple, clean hard-surface)
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=0.08)
    bpy.ops.object.mode_set(mode='OBJECT')
    return ob


def seat_transform(seat):
    th = math.radians(seat["rake_deg"])
    return Matrix.Translation(Vector(seat["loc"])) @ Matrix.Rotation(th, 4, 'X').to_4x4()


def composite(tag, gun_path, mag_path, seat):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=gun_path)
    gun_objs = [o for o in bpy.context.scene.objects if o not in before and o.type == "MESH"]
    bpy.ops.import_scene.fbx(filepath=mag_path)
    mag_src = [o for o in bpy.context.scene.objects if o not in before and o.type == "MESH" and "ExtMag" in o.name][-1]
    for o in gun_objs:
        m = bpy.data.materials.new(o.name + "_f"); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.52, 0.53, 0.55, 1)
        b.inputs["Roughness"].default_value = 0.6
        o.data.materials.clear()
        o.data.materials.append(m)
        o.hide_render = o.name.startswith("SK_Manny")
    mag = mag_src.copy()
    mag.data = mag_src.data.copy()
    bpy.context.scene.collection.objects.link(mag)
    mag_src.hide_render = True
    mag.matrix_world = seat_transform(seat)
    m = bpy.data.materials.new("magprev"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.06, 0.06, 0.065, 1)
    b.inputs["Roughness"].default_value = 0.5
    mag.data.materials.clear()
    mag.data.materials.append(m)
    scene = bpy.context.scene
    cd = bpy.data.cameras.new("c"); cd.type = 'ORTHO'; cd.ortho_scale = 0.5
    cam = bpy.data.objects.new("c", cd); scene.collection.objects.link(cam)
    loc = Vector(seat["loc"]) + Vector((0, 0.02, -0.08))
    d = Vector((1, -0.35, -0.15)).normalized()
    z = -d; x = Vector((0, 0, 1)).cross(z).normalized(); y = z.cross(x)
    cam.matrix_world = Matrix.Translation(loc - d * 2) @ Matrix((x, y, z)).transposed().to_4x4()
    scene.camera = cam
    sun = bpy.data.lights.new("s", 'SUN'); sun.energy = 3.5
    so = bpy.data.objects.new("s", sun); scene.collection.objects.link(so)
    so.rotation_euler = (math.radians(55), 0, math.radians(35))
    w = bpy.data.worlds.new("w"); w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.9, 0.92, 1)
    scene.world = w
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = scene.render.resolution_y = 1100
    scene.render.filepath = os.path.join(REF, f"compose_{tag}.png")
    bpy.ops.render.render(write_still=True)
    # pure side view too
    d2 = Vector((1, 0, 0))
    z = -d2; x = Vector((0, 0, 1)).cross(z).normalized(); y = z.cross(x)
    cam.matrix_world = Matrix.Translation(loc - d2 * 2) @ Matrix((x, y, z)).transposed().to_4x4()
    scene.render.filepath = os.path.join(REF, f"compose_{tag}_side.png")
    bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ob, straight_end, total = build_mag()
    add_details(ob, straight_end, total)
    n_tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print("EXTMAG tris:", n_tris, "verts:", len(ob.data.vertices))

    if EXPORT:
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        os.makedirs(OUT, exist_ok=True)
        bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "SM_ExtMag_Universal.fbx"),
                                 use_selection=True, object_types={'MESH'},
                                 axis_forward='-Y', axis_up='Z', bake_anim=False,
                                 mesh_smooth_type='FACE', use_tspace=True)
        print("EXTMAG_EXPORTED")

    mag_path = os.path.join(OUT, "SM_ExtMag_Universal.fbx")
    for gun, path in GUNS.items():
        composite(gun, path, mag_path, SEATS[gun])

    # seat constants for C++ (armature-space == WPN_root-local metre frame)
    consts = {}
    for gun, seat in SEATS.items():
        th = math.radians(seat["rake_deg"])
        q = BQuat((1, 0, 0), th)
        consts[gun] = {
            "loc": list(seat["loc"]),
            "quat_xyzw": [round(v, 8) for v in q],
            "rake_deg": seat["rake_deg"],
        }
    with open(os.path.join(REF, "seat_constants.json"), "w", encoding="utf-8") as fh:
        json.dump(consts, fh, indent=1)
    print("EXTMAG_DONE")


main()
