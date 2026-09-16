"""Fix two defects reported by the user.

1. Column had open shells / seams: the revolve profiles never returned to the axis, so each
   segment was an open surface of revolution, and segments only touched face-to-face. Now the
   profiles close to the axis, the segments overlap, and the whole thing is merged with
   SelfUnion into one watertight manifold before the flutes are cut.
2. The entablature had no collision: enable_collision on save is only a flag. Collision
   geometry is generated explicitly here (aligned boxes suit a beam).
"""

import math

import unreal

SV = unreal.ModelingService
DIR = "/Game/Props/RomanColumn20260915"
MESH = DIR + "/SM_RomanColumn_Detailed"
ENTAB = DIR + "/SM_Colonnade_Entablature"
MAT = DIR + "/M_Plaster_Detailed"
NOISE = DIR + "/T_PlasterNoise"

LOG = []


def log(message):
    print("[fix] " + message)


def tf(x=0.0, y=0.0, z=0.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(0.0, 0.0, 0.0).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def v2(radius, height):
    return unreal.Vector2D(radius, height)


def do(label, result):
    ok = getattr(result, "success", None)
    msg = getattr(result, "message", "")
    LOG.append((label, ok, msg))
    log("%-24s %s %s" % (label, ok, msg))
    return result


# ---------------------------------------------------------------- profiles
# Overlapping bands (0.5 cm) so nothing merely touches face to face.
shaft_bottom_z, shaft_top_z = 29.5, 230.5
shaft_height = shaft_top_z - shaft_bottom_z
r_bottom, r_top, r_swell = 21.4, 20.6, 22.05


def shaft_radius(z):
    t = (z - shaft_bottom_z) / shaft_height
    linear = r_bottom + (r_top - r_bottom) * t
    swell = (r_swell - max(r_bottom, r_top)) * math.sin(math.pi * min(t / 0.62, 1.0))
    return linear + max(0.0, swell)


# Every profile now starts and ends on the axis (radius 0) so the lathe closes into a solid.
base_profile = [v2(0.0, 11.5)] + [
    v2(38.0, 11.5), v2(38.0, 13.5), v2(34.5, 15.0), v2(33.6, 16.6),
    v2(33.0, 17.0), v2(31.4, 18.6), v2(28.8, 20.2), v2(26.6, 21.8),
    v2(25.6, 23.0), v2(27.2, 23.9), v2(28.2, 25.1), v2(28.2, 26.9),
    v2(27.2, 28.1), v2(25.6, 29.0), v2(23.4, 29.8), v2(22.2, 30.5),
] + [v2(0.0, 30.5)]

shaft_profile = [v2(0.0, shaft_bottom_z)] + [
    v2(shaft_radius(z), z)
    for z in [shaft_bottom_z + shaft_height * i / 24.0 for i in range(25)]
] + [v2(0.0, shaft_top_z)]

capital_profile = [v2(0.0, 229.5)] + [
    v2(22.2, 229.5), v2(21.6, 231.2), v2(20.4, 232.6), v2(20.2, 234.0),
    v2(20.8, 236.0), v2(22.4, 238.0), v2(24.6, 241.0), v2(27.2, 244.0),
    v2(29.6, 247.0), v2(31.2, 249.5), v2(32.0, 251.0), v2(32.0, 252.5),
] + [v2(0.0, 252.5)]

# ---------------------------------------------------------------- rebuild
mesh = do("create_mesh", SV.create_mesh()).handle
do("plinth", SV.append_box(mesh, tf(0, 0, 0), 76.0, 76.0, 12.5, 0, 0, 0, "Base", 0))
do("base_revolve", SV.append_revolve_polygon(mesh, tf(), base_profile, 0.0, 64, 360.0, 0))
do("shaft_revolve", SV.append_revolve_polygon(mesh, tf(), shaft_profile, 0.0, 64, 360.0, 0))
do("capital_revolve", SV.append_revolve_polygon(mesh, tf(), capital_profile, 0.0, 64, 360.0, 0))
do("abacus", SV.append_box(mesh, tf(0, 0, 251.5), 66.0, 66.0, 10.5, 0, 0, 0, "Base", 0))
do("abacus_crown", SV.append_box(mesh, tf(0, 0, 261.5), 62.0, 62.0, 3.5, 0, 0, 0, "Base", 0))

before = SV.get_mesh_info(mesh)
log("before union: closed=%s open_edges=%s components=%s tris=%s" % (
    before.is_closed, before.open_border_edges, before.connected_components, before.triangle_count))

try:
    do("self_union", SV.self_union(mesh, True, True))
except TypeError:
    do("self_union", SV.self_union(mesh))

after = SV.get_mesh_info(mesh)
log("after union:  closed=%s open_edges=%s components=%s tris=%s" % (
    after.is_closed, after.open_border_edges, after.connected_components, after.triangle_count))

# ------------------------------------------------------------------- flutes
tool = SV.create_mesh().handle
flutes = 20
for index in range(flutes):
    angle = 2.0 * math.pi * index / flutes
    SV.append_cylinder(tool, tf(math.cos(angle) * 22.5, math.sin(angle) * 22.5, 31.0),
                       2.0, 198.0, 24, 0, True, "Base", 0)
do("flute_boolean", SV.boolean(mesh, tool, "Subtract", tf(), True, True))
SV.release_mesh(tool)

cut = SV.get_mesh_info(mesh)
log("after flutes: closed=%s open_edges=%s components=%s tris=%s" % (
    cut.is_closed, cut.open_border_edges, cut.connected_components, cut.triangle_count))

try:
    do("weld_edges", SV.weld_edges(mesh, 0.001))
except TypeError:
    pass
try:
    do("simplify_planar", SV.simplify_planar(mesh, 0.01))
except Exception as exc:  # noqa: BLE001
    log("simplify skipped: %s" % exc)

# ------------------------------------------------------------- uv / detail
do("auto_uv", SV.auto_uv(mesh, "XAtlas", 0))
log("uv: " + str(SV.get_uv_stats(mesh, 0, 512)))
do("displace", SV.displace_from_texture(mesh, "", NOISE + "." + NOISE.split("/")[-1], 0.12, 0))

do("save_mesh", SV.save_mesh_to_static_mesh(mesh, MESH, True, True, False, True))
do("column_collision", SV.generate_collision(MESH, "ConvexHulls", 10, 25, True))
do("assign_material", SV.set_asset_materials(MESH, MAT, True))
SV.release_mesh(mesh)

# ------------------------------------------- entablature: real collision geom
do("entablature_collision", SV.generate_collision(ENTAB, "AlignedBoxes", 1, 25, True))

beam = unreal.EditorAssetLibrary.load_asset(ENTAB)
body = beam.get_editor_property("body_setup") if beam else None
log("entablature body_setup: %s" % (body.get_path_name() if body else "None"))
if body:
    for field in ("box_elems", "convex_elems", "sphere_elems", "agg_geom"):
        try:
            print("[fix]   %s -> %s" % (field, len(body.get_editor_property(field))))
        except Exception as exc:  # noqa: BLE001
            print("[fix]   %s unavailable (%s)" % (field, exc))

log("=== summary ===")
bad = [entry for entry in LOG if entry[1] is False]
for label, ok, msg in bad:
    log("  FAILED %s %s" % (label, msg))
log("steps=%d failed=%d" % (len(LOG), len(bad)))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
