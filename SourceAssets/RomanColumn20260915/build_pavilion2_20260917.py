"""Roman domed pavilion v2 — bigger plan, true hemispherical dome, coffered soffit.

Supersedes the 2026-09-16 pavilion (32-cell plan, 8 columns, "dome" that is a straight
cone because the original build ran self_union(True, True) — bTrimFlaps eats the arc).

Everything is centimetres on the 20 cm build grid; each piece's bbox is an exact cell
multiple so the palette footprint self-check passes.

  base   SM_RomanPavilionBase_20    disc r480, 20 tall              48 x 48 x  1 cells
  10 columns on ring radius 360     SM_RomanColumn_Round_20, 260 tall (round plates)
  arch   SM_RomanPavilionArch_20    entablature ring r320-480,
                                    z 280-360, 72 dentils           48 x 48 x  4 cells
  dome   SM_RomanPavilionDome_20    hemisphere shell, soffit r360, oculus r72,
                                    5 coffer rows x 28, stepped extrados
                                                                    44 x 44 x 20 cells

Proportions, all from the Pantheon survey literature (Aliberti & Alonso-Rodriguez 2017,
Martines/Wilson Jones in *The Pantheon*, Vitruvius III-IV) at a 1 : 6.1 scale:

  * interior diameter 720, interior height to the oculus 740 -> the Pantheon's 1:1 rule
    (its springing sits at half the total height, apex at the diameter).
  * hemisphere, not a cone: mid-height radius 0.866 R against a cone's 0.50 R.
  * coffers: 5 rows x 28 (140, the Pantheon count), row angular height dphi = k sin(phi)
    with k = 0.78 * 2pi/N so rows shorten towards the crown instead of freezing into the
    even grid that makes domes read as tents; top ~28 % of the arc stays a plain calotte.
  * coffer depth ~1/5 of coffer width (0.67 m on 3.88 m at the Pantheon), bands 0.84 m
    and meridian ribs ~1.0 m, both divided by 6.1.
  * oculus = 1/5 of the span (0.20 here against the Pantheon's 0.202).
  * extrados carries stepped rings over the lower half of the rise (the Pantheon's 7
    rings); coffering is an intrados feature — all 140 Pantheon coffers are inside.

The soffit is left open (oculus r72), so the pavilion is an umbrella rather than a rain
shelter. Set CLOSE_OCULUS = True to build the capped variant instead (same mesh, the
shell profile simply runs on to the apex).

Run headless (editor must be closed so the asset lock is free):
  UnrealEditor-Cmd <uproject> -run=pythonscript -script=<this> -unattended -NullRHI -nosplash
"""

import math
import os
import time

import unreal

SV = unreal.ModelingService
DIR = "/Game/Props/RomanColumn20260915"
BASE_PATH = DIR + "/SM_RomanPavilionBase_20"
ARCH_PATH = DIR + "/SM_RomanPavilionArch_20"
DOME_PATH = DIR + "/SM_RomanPavilionDome_20"
MAT = DIR + "/M_RomanStone_V2"
# the pavilion uses the round-plate column variant (square bases/abaci read wrong on a
# circular colonnade); the linear colonnade keeps SM_RomanColumn_Detailed
COLUMN_PATH = DIR + "/SM_RomanColumn_Round_20"

# ------------------------------------------------------------------ dimensions
V = 20.0                       # build grid cell (cm)

R_STYLO = 480.0                # stylobate outer radius
R_STYLO_TOP = 460.0            # stylobate upper step radius
H_STYLO = 20.0

R_COL = 360.0                  # column ring radius
N_COL = 10

Z_ARCH0 = 280.0                # entablature underside = column top
Z_ARCH1 = 360.0                # entablature top = dome springing
R_ARCH_IN = 320.0              # inner edge, flush with the column base inner edge
R_ARCH_FACE = 400.0            # body face, flush with the column base outer edge
R_ARCH_OUT = 440.0             # cornice projection (40 past the wall, no brim)
N_DENTIL = 72
DENTIL_W = 16.0
DENTIL_D = 40.0
DENTIL_H = 16.0

R_OUT = 400.0                  # dome reference radius (hemisphere extrados above the steps)
R_IN = 360.0                   # dome soffit radius
R_OC = 72.0                    # oculus radius
CLOSE_OCULUS = True            # False builds the open-oculus variant (collar ring)
STEPS = 96                     # revolve segments
ARC_STEP_DEG = 2.5             # extrados / soffit sampling

LEDGE_ALPHAS = (74.0, 66.0, 58.0)   # stepped extrados rings, lower half of the rise
LEDGE_DROP = 5.0                    # radial inset per ring (shell is only 40 cm at the base,
                                    # so the rings inset — they never flare outside r = R_OUT)
TAPER_END = 48.0                    # the inset fades back to the plain hemisphere by here

COFFER_TOP = 88.0              # coffer field starts here (plain moulded band at the foot)
ROW_COFFERS = 28               # Pantheon: constant 28-coffer sectors in every row
ROW_COUNT = 5
K_ROW = 0.78 * 2.0 * math.pi / ROW_COFFERS    # row height coefficient (Pantheon 0.176 rad)
BAND_CM = 14.0                 # ring rib width on the surface (Pantheon 0.84 m / 6.1)
RIB_W = 16.0                   # meridian rib width (Pantheon ~1.0 m / 6.1)
RIB_H = 13.0                   # coffer depth = rib relief (Pantheon 1/5 of coffer width)
RIB_EMBED = 4.0                # rib depth buried in the shell (coincident faces z-fight)

LEVEL = "/Game/GameMaps/DayNight_Lighting"
# The bigger plan no longer clears the colonnade marble floor (its edge sits at y=150),
# so the pavilion moves back 400: rim at y=+80, floor edge at y=150, 70 cm of clearance.
PAVILION_ORIGIN = (1350.0, -400.0)

LOG = []
STARTED = time.time()


def log(message):
    print("[pv2] " + message)


def do(label, result):
    ok = getattr(result, "success", None)
    LOG.append((label, ok))
    log("%-24s %s" % (label, ok))
    return result


def tf(x=0.0, y=0.0, z=0.0, pitch=0.0, yaw=0.0, roll=0.0):
    """Transform with a rotator built from named angles.

    UE 5.8's Python Rotator ctor takes (roll, pitch, yaw) positionally — probed, not
    assumed: Rotator(10, 20, 30) reads back pitch=20 yaw=30 roll=10. Passing UE's C++
    (pitch, yaw, roll) order silently rotates about the wrong axes (the dome ribs ended
    up mirrored under the springing plane that way).
    Also note the local frame after Rotator(pitch=-alpha, yaw=theta): local X runs down
    the meridian, local Y is tangential, local Z is the surface normal — so a template
    box must be built depth-on-X and width-on-Y.
    """
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(roll, pitch, yaw).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def v2(radius, height):
    return unreal.Vector2D(radius, height)


def wait(path, timeout=20.0):
    end = time.time() + timeout
    while time.time() < end:
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if asset:
            return asset
        time.sleep(0.3)
    return None


# Collision method note: "ConvexHulls" can weld several separate shells of one mesh into a
# single blob (the pavilion arch asked for 8 hulls on a ring and got a solid disc, the
# colonnade rack got 852 hulls for ten columns). "AlignedBoxes" emits one axis-aligned box per
# connected shell — a box per column, a box per dentil — which is what a building piece wants
# and is the only collision I can still reason about with certainty, since headless physics
# queries do not answer for level geometry.
def collision_summary(path):
    """Shape counts straight out of the asset: the only collision evidence available headless.

    A box per connected shell is what AlignedBoxes gives; any convex_elems left over means some
    shell was welded into a blob, which is what can silently plug the space between columns.
    """
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    setup = mesh.get_editor_property("body_setup") if mesh else None
    if not setup:
        return None
    agg = None
    for prop in ("agg_geom", "aggregate_geometry"):
        try:
            agg = setup.get_editor_property(prop)
        except Exception:
            continue
        if agg:
            break
    if not agg:
        return {}
    counts = {}
    for elem in ("box_elems", "convex_elems", "sphere_elems", "sphyl_elems", "taper_elems"):
        try:
            arr = agg.get_editor_property(elem)
            if arr:
                counts[elem.replace("_elems", "")] = len(arr)
        except Exception:
            pass
    return counts


def collision_summary(path):
    """Shape counts straight out of the asset (headless physics cannot answer)."""
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    setup = mesh.get_editor_property("body_setup") if mesh else None
    if not setup:
        return None
    agg = None
    for prop in ("agg_geom", "aggregate_geometry"):
        try:
            agg = setup.get_editor_property(prop)
        except Exception:
            continue
        if agg:
            break
    counts = {}
    if agg:
        for elem in ("box_elems", "convex_elems", "sphere_elems", "sphyl_elems", "taper_elems"):
            try:
                arr = agg.get_editor_property(elem)
                counts[elem.replace("_elems", "")] = len(arr) if arr else 0
            except Exception:
                pass
    return counts


def make_triangle_collision(path):
    """Shells and rings: drop the generated simple shapes and let the mesh be the collision.

    The generators handed the dome an oversized capsule (a "sphyl" element) that reached from
    its springing at z=360 all the way to the ground, so the dome's collision plugged the whole
    pavilion and every bay — the player could not walk in. A hollow shell has no meaningful
    box/hull approximation anyway; complex-as-simple keeps the interior open and still stops
    bullets on the shell.
    """
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    setup = mesh.get_editor_property("body_setup") if mesh else None
    if not setup:
        log("no body setup for %s" % path)
        return False
    for prop in ("agg_geom", "aggregate_geometry"):
        try:
            agg = setup.get_editor_property(prop)
        except Exception:
            continue
        if not agg:
            continue
        for elem in ("box_elems", "convex_elems", "sphere_elems", "sphyl_elems", "taper_elems"):
            try:
                agg.set_editor_property(elem, [])
            except Exception:
                pass
        break
    setup.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    return True


def disk_stamp(path):
    """In-process success is not evidence: the arch asset once reported a save and stayed
    stale on disk. Only the file's size and mtime count."""
    full = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())         + path.split("/Game/", 1)[1] + ".uasset"
    if not os.path.exists(full):
        return None
    st = os.stat(full)
    return st.st_size, time.strftime("%H:%M:%S", time.localtime(st.st_mtime)), st.st_mtime


def publish(handle, path, method="AlignedBoxes", hulls=8):
    do("uv", SV.auto_uv(handle, "XAtlas", 0))
    do("save", SV.save_mesh_to_static_mesh(handle, path, True, True, False, True))
    SV.release_mesh(handle)
    asset = wait(path)
    if not asset:
        log("MISSING after save: %s" % path)
        return None
    stamp = disk_stamp(path)
    fresh = bool(stamp and stamp[2] >= STARTED - 5.0)
    # A stale stamp means the write lost a sharing race (MoveFile error 32 — OneDrive/AV
    # holding the freshly written .uasset); save_loaded_asset retries after the lock clears.
    for attempt in range(4):
        if fresh:
            break
        log("disk STALE, retry %d in 4 s" % (attempt + 1))
        time.sleep(4.0)
        unreal.EditorAssetLibrary.save_loaded_asset(asset, True)
        stamp = disk_stamp(path)
        fresh = bool(stamp and stamp[2] >= STARTED - 5.0)
    LOG.append(("disk_" + path.rsplit("/", 1)[-1], fresh))
    log("disk %-28s %s %s" % (path.rsplit("/", 1)[-1],
                              "%d B / %s" % (stamp[0], stamp[1]) if stamp else "missing",
                              "FRESH" if fresh else "STALE (save did not land!)"))
    do("collision", SV.generate_collision(path, method, hulls, 25, True))
    counts = collision_summary(path) or {}
    # A shell or a ring must not carry a generated solid: the dome's came out with a capsule
    # spanning the whole pavilion. Those get their triangles as collision instead.
    hollow = any(counts.get(k) for k in ("sphere", "sphyl", "taper")) or path.rsplit("/", 1)[-1].startswith(
        ("SM_RomanPavilionDome", "SM_RomanPavilionArch"))
    if hollow:
        make_triangle_collision(path)
        counts = collision_summary(path) or {}
        log("collision %-28s %s -> triangle collision (shell/ring)" % (path.rsplit("/", 1)[-1], counts))
        LOG.append(("collision_shapes_" + path.rsplit("/", 1)[-1],
                    not any(counts.get(k) for k in ("box", "convex", "sphere", "sphyl", "taper"))))
    else:
        boxes_only = bool(counts.get("box")) and not counts.get("convex")
        LOG.append(("collision_shapes_" + path.rsplit("/", 1)[-1], boxes_only))
        log("collision %-28s %s %s" % (path.rsplit("/", 1)[-1], counts,
                                       "OK (box per shell)" if boxes_only else "UNEXPECTED"))
    do("material", SV.set_asset_materials(path, MAT, True))
    bb = asset.get_bounds()
    log("   %-28s bbox %.0f x %.0f x %.0f  tris=%d" % (path.rsplit("/", 1)[-1],
                                                      bb.box_extent.x * 2, bb.box_extent.y * 2,
                                                      bb.box_extent.z * 2, asset.get_num_triangles(0)))
    return asset


def info(handle, label):
    i = SV.get_mesh_info(handle)
    log("%-22s tris=%d comps=%d open=%d h=%.1f rmax=%.1f" % (
        label, i.triangle_count, i.connected_components, i.open_border_edges,
        i.bounds_max.z - i.bounds_min.z, max(abs(i.bounds_max.x), abs(i.bounds_min.x))))
    return i


def z_extent(handle):
    """True vertex z range: get_mesh_info bounds are boxy, this is the geometry itself."""
    dm = SV.get_dynamic_mesh(handle)
    _, tlist, _ = dm.get_all_triangle_i_ds()
    hi = lo = None
    for tid in tlist.convert_index_list_to_array():
        ok, v1, v2_, v3 = dm.get_triangle_positions(int(tid))
        for p in (v1, v2_, v3):
            if hi is None or p.z > hi.z:
                hi = p
            if lo is None or p.z < lo.z:
                lo = p
    return lo.z, hi.z


# =============================================================== 1. stylobate
base = SV.create_mesh().handle
# Two 10 cm steps instead of one 20 cm lip: with an uneven ground a single 20 cm edge sits
# right at the character's 40 cm step limit (FPSGAMECharacter.cpp:187), which strands the
# player outside the colonnade. 10 cm each climbs anywhere.
SV.append_revolve_polygon(base, tf(), [
    v2(0.0, 0.0), v2(R_STYLO, 0.0), v2(R_STYLO, 10.0),
    v2(R_STYLO - 14.0, 10.0), v2(R_STYLO - 20.0, H_STYLO), v2(0.0, H_STYLO),
], 0.0, STEPS, 360.0, 0)
info(base, "base raw")
publish(base, BASE_PATH, "AlignedBoxes", 1)

# ============================================================= 2. entablature
arch = SV.create_mesh().handle
# PROFILE Z IS LOCAL (0 at the piece's own foot). Writing absolute world heights here instead
# (280/360) shifted the whole mesh 280 above its pivot: the piece then floated a storey above
# the columns and its ring poked out through the upper dome.
H_ARCH = Z_ARCH1 - Z_ARCH0
# Width: the soffit runs all the way out to the column's outer edge (r400), so the beam sits
# exactly on the capital's round abacus (r320-400) and the abacus cannot stick out past it.
# Every face above the soffit is at r >= 394, i.e. still covering the abacus's edge.
arch_profile = [
    v2(R_ARCH_IN, 0.0),              # inner bottom corner (the soffit starts here)
    v2(R_ARCH_FACE, 0.0),            # soffit out to r400 = the abacus edge
    v2(R_ARCH_FACE - 4.0, 8.0),      # cyma steps in just above the abacus
    v2(R_ARCH_FACE - 4.0, 26.0),     # architrave face
    v2(R_ARCH_FACE, 30.0),           # taenia back out to r400
    v2(R_ARCH_FACE, 40.0),
    v2(R_ARCH_FACE - 6.0, 44.0),     # frieze, barely recessed
    v2(R_ARCH_FACE - 6.0, 60.0),     # frieze face
    v2(R_ARCH_FACE + 2.0, 62.0),     # bed mould out
    v2(R_ARCH_FACE + 2.0, 68.0),     # dentil band background
    v2(R_ARCH_FACE + 12.0, 72.0),    # cornice slope
    v2(R_ARCH_OUT, 76.0),            # cornice face
    v2(R_ARCH_OUT, H_ARCH),          # cornice top
    v2(R_ARCH_FACE, H_ARCH),         # dome seat (r400 = dome base)
    v2(R_ARCH_IN, H_ARCH),
]
SV.append_revolve_polygon(arch, tf(), arch_profile, 0.0, STEPS, 360.0, 0)

# dentils: one template box, batched into place around the ring
# local X = radial, local Y = tangential after Rotator(pitch=0, yaw=theta)
dentil = SV.create_mesh().handle
SV.append_box(dentil, tf(0.0, 0.0, 0.0), DENTIL_D, DENTIL_W, DENTIL_H, 0, 0, 0, "Center", 0)
dentil_at = []
r_dentil = R_ARCH_FACE + 4.0
z_dentil = 64.0          # local, like the profile
for k in range(N_DENTIL):
    theta = 360.0 * k / N_DENTIL
    dentil_at.append(tf(r_dentil * math.cos(math.radians(theta)),
                        r_dentil * math.sin(math.radians(theta)), z_dentil, 0.0, theta, 0.0))
SV.append_mesh_at_transforms(arch, dentil, dentil_at)
SV.release_mesh(dentil)
info(arch, "arch raw")
publish(arch, ARCH_PATH, "AlignedBoxes", 1)

# ==================================================================== 3. dome
dome = SV.create_mesh().handle
a_out = 0.0 if CLOSE_OCULUS else math.degrees(math.asin(R_OC / R_OUT))
a_in = 0.0 if CLOSE_OCULUS else math.degrees(math.asin(R_OC / R_IN))


def sphere_point(radius, alpha_deg):
    a = math.radians(alpha_deg)
    return radius * math.sin(a), radius * math.cos(a)


def is_ledge(alpha):
    return any(abs(alpha - la) < 1e-9 for la in LEDGE_ALPHAS)


def ledge_offset(alpha):
    """Extrados inset at alpha (0 on the plain hemisphere, negative inside a ring).

    The rings step inward going up from the springing, and the third ring's inset fades
    linearly back to the hemisphere so the calotte above stays a clean dome. Kept inside
    r = R_OUT so the dome never overhangs the colonnade: at 400 it is plumb with the
    architrave face and with the outer edge of the column bases.
    """
    if alpha > LEDGE_ALPHAS[0]:
        return 0.0
    if alpha >= LEDGE_ALPHAS[-1]:
        rings = sum(1 for la in LEDGE_ALPHAS if alpha <= la + 1e-9)
        return -LEDGE_DROP * rings
    if alpha <= TAPER_END:
        return 0.0
    return -LEDGE_DROP * len(LEDGE_ALPHAS) * (alpha - TAPER_END) / (LEDGE_ALPHAS[-1] - TAPER_END)


def extrados():
    """Outer profile from the springing up to the oculus, with the stepped rings.

    Each ring keeps the dome fatter than a plain hemisphere and ends in a horizontal
    ledge — the Pantheon's extrados treatment (coffering there is intrados-only).
    """
    samples, a = [], 90.0
    while a > a_out:
        samples.append(a)
        a -= ARC_STEP_DEG
    samples.append(a_out)
    samples += [la for la in LEDGE_ALPHAS]
    points = []
    for alpha in sorted(set(samples), reverse=True):
        if alpha < a_out - 1e-9:
            continue
        r, z = sphere_point(R_OUT, alpha)
        off = ledge_offset(alpha)
        if is_ledge(alpha):
            points.append((r + off + LEDGE_DROP, z))   # the ring face keeps the outer radius
        points.append((r + off, z))
    return points


N_IN = max(2, int(round((90.0 - a_in) / ARC_STEP_DEG)))
shell = [v2(*p) for p in extrados()]
if not CLOSE_OCULUS:
    shell.append(v2(R_OC, sphere_point(R_IN, a_in)[1]))                # oculus collar wall
# soffit back down from the oculus edge to the springing (the closing edge lays the base ring)
shell += [v2(*sphere_point(R_IN, 90.0 - (90.0 - a_in) * k / N_IN))
          for k in range(N_IN if CLOSE_OCULUS else N_IN - 1, -1, -1)]
SV.append_revolve_polygon(dome, tf(), shell, 0.0, STEPS, 360.0, 0)
log("shell profile: %d points, extrados rings at %s" % (len(shell), list(LEDGE_ALPHAS)))
info(dome, "dome shell")

if not CLOSE_OCULUS:
    # exterior oculus collar: raised rim, tops out exactly at the apex height (bbox = 20 cells)
    collar = SV.create_mesh().handle
    r_collar = R_OC + 28.0
    z_oc_out = sphere_point(R_OUT, a_out)[1]
    z_collar = math.sqrt(max(R_OUT ** 2 - r_collar ** 2, 0.0))
    SV.append_revolve_polygon(collar, tf(), [
        v2(R_OC, z_oc_out), v2(r_collar, z_collar), v2(r_collar, R_OUT), v2(R_OC, R_OUT),
    ], 0.0, STEPS, 360.0, 0)
    SV.append_mesh(dome, collar, tf())
    SV.release_mesh(collar)

# --------------------------------------------------------------- coffer rows
# Pantheon generative rule: constant 28-coffer sectors, row angular height dphi = k sin(phi),
# so rows shorten towards the crown and the top of the arc stays a plain calotte.
band_deg = math.degrees(BAND_CM / R_IN)
alphas, phi = [COFFER_TOP], COFFER_TOP
for _ in range(ROW_COUNT):
    phi -= math.degrees(K_ROW * math.sin(math.radians(phi))) + band_deg
    alphas.append(max(phi, a_in))
log("coffer rows: %d x %d coffers, boundaries %s, plain calotte from %.1f deg to the apex/oculus"
    % (ROW_COUNT, ROW_COFFERS, ["%.1f" % a for a in alphas], alphas[-1]))


def rib_ring(alpha_deg):
    """Closed quad profile that follows the sphere at alpha_deg (counter-clockwise).

    The room is inside the sphere, so the relief reaches R_IN - RIB_H and the buried part
    sits at R_IN + RIB_EMBED (never exactly on the soffit: coincident faces z-fight).
    """
    half = math.degrees(BAND_CM / 2.0 / (R_IN * math.sin(math.radians(alpha_deg))))
    lo, hi = alpha_deg - half, alpha_deg + half
    inner = [sphere_point(R_IN - RIB_H, alpha) for alpha in (lo, hi)]
    outer = [sphere_point(R_IN + RIB_EMBED, alpha) for alpha in (lo, hi)]
    return [v2(*inner[0]), v2(*inner[1]), v2(*outer[1]), v2(*outer[0])]


for alpha in alphas:               # every row boundary, including the field's lower edge
    SV.append_revolve_polygon(dome, tf(), rib_ring(alpha), 0.0, STEPS, 360.0, 0)
info(dome, "dome + ring ribs")

# Meridional ribs: one box template per row (its length follows the row's arc), placed by
# Rotator(pitch=-alpha, yaw=theta). Rows shorten towards the crown, so each row gets its own
# template rather than one global length.
total_ribs = 0
for row in range(ROW_COUNT):
    lo, hi = alphas[row + 1], alphas[row]
    arc_cm = math.radians(hi - lo) * R_IN
    segs = max(2, int(round(arc_cm / (RIB_W * 1.6))))
    seg_len = 2.0 * R_IN * math.sin(math.radians((hi - lo) / segs / 2.0)) * 1.05
    tmpl = SV.create_mesh().handle
    SV.append_box(tmpl, tf(0.0, 0.0, R_IN - (RIB_H - RIB_EMBED) / 2.0),
                  seg_len, RIB_W, RIB_H + RIB_EMBED, 0, 0, 0, "Center", 0)
    row_at = []
    for j in range(ROW_COFFERS):
        theta = 360.0 * j / ROW_COFFERS
        for s in range(segs):
            a_seg = lo + (hi - lo) * (s + 0.5) / segs
            row_at.append(tf(0.0, 0.0, 0.0, -a_seg, theta, 0.0))
    SV.append_mesh_at_transforms(dome, tmpl, row_at)
    SV.release_mesh(tmpl)
    total_ribs += len(row_at)
    log("  row %d: %.1f-%.1f deg, %d coffers x %d segments (%.0f cm each)"
        % (row + 1, lo, hi, ROW_COFFERS, segs, seg_len))
log("radial rib instances: %d over %d coffers" % (total_ribs, ROW_COFFERS * ROW_COUNT))
info(dome, "dome + radial ribs")

# --- functional check: a point on a rib must be inside, a coffer centre must be outside
probe_r = R_IN - RIB_H * 0.5          # mid-relief: ribs reach it, bare soffit does not
rib_ok = SV.is_point_inside(dome, unreal.Vector(
    probe_r * math.sin(math.radians(alphas[1])), 0.0, probe_r * math.cos(math.radians(alphas[1]))))
row_mid = (alphas[0] + alphas[1]) / 2.0
theta_half = 360.0 / (2.0 * ROW_COFFERS)
coffer_pt = unreal.Vector(
    probe_r * math.sin(math.radians(row_mid)) * math.cos(math.radians(theta_half)),
    probe_r * math.sin(math.radians(row_mid)) * math.sin(math.radians(theta_half)),
    probe_r * math.cos(math.radians(row_mid)))
coffer_ok = SV.is_point_inside(dome, coffer_pt)
log("probe: rib interior=%s (want True), coffer void=%s (want False)" % (rib_ok, coffer_ok))
log("probe: plain calotte %.0f deg -> %s, arc %.0f cm" % (
    alphas[-1], "apex" if CLOSE_OCULUS else "oculus", math.radians(alphas[-1]) * R_IN))

lo_z, hi_z = z_extent(dome)
log("vertex z range: %.2f .. %.2f (want 0 .. %.1f)" % (lo_z, hi_z, R_OUT))
geometry_ok = abs(lo_z) < 0.5 and abs(hi_z - R_OUT) < 0.5
info(dome, "dome final")
publish(dome, DOME_PATH, "AlignedBoxes", 1)

# =============================================================== 4. scene swap
# Only touch the level once the coffers actually read as coffers; the old pavilion
# actors stay put if the probe failed.
if rib_ok and not coffer_ok and geometry_ok:
    sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    try:
        sub.load_level(LEVEL)
    except Exception as exc:
        log("level load: %s" % exc)
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    removed = 0
    for a in list(actor_sub.get_all_level_actors()):
        if a.get_actor_label().startswith(("Pavilion_", "RomanPavilion2_")):
            actor_sub.destroy_actor(a)
            removed += 1
    log("removed %d existing pavilion actors" % removed)

    # spawn_static_mesh_actor goes through SpawnActorFromObject, which returns nothing in a
    # commandlet ("No actor was spawned"); EditorActorSubsystem.spawn_actor_from_class works.
    def spawn(mesh_path, location, label):
        mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
        actor = actor_sub.spawn_actor_from_class(unreal.StaticMeshActor, location,
                                                 unreal.Rotator(0.0, 0.0, 0.0))
        if not actor or not mesh:
            log("spawn failed: %s" % label)
            return None
        actor.set_actor_label(label)
        smc = actor.static_mesh_component
        if smc.mobility != unreal.ComponentMobility.MOVABLE:
            smc.set_mobility(unreal.ComponentMobility.MOVABLE)
        smc.set_static_mesh(mesh)
        smc.set_material(0, unreal.EditorAssetLibrary.load_asset(MAT))
        return actor

    ox, oy = PAVILION_ORIGIN
    placed = 0
    # each piece's mesh must sit on z=0 locally, otherwise the actor z below is a lie: the
    # first build wrote absolute heights into the arch profile and left an 80 cm gap with the
    # entablature floating through the dome. Assert the stack closes before spawning.
    expected = ((BASE_PATH, 0.0, 20.0), (COLUMN_PATH, V, 280.0),
                (ARCH_PATH, Z_ARCH0, Z_ARCH1), (DOME_PATH, Z_ARCH1, Z_ARCH1 + 400.0))
    for path, z0, z1 in expected:
        mesh = wait(path, 10.0)
        bb = mesh.get_bounds()
        lo, hi = bb.origin.z - bb.box_extent.z, bb.origin.z + bb.box_extent.z
        ok = abs(lo) < 0.5
        LOG.append(("pivot_" + path.rsplit("/", 1)[-1], ok))
        log("pivot %-30s local z %.1f..%.1f %s" % (path.rsplit("/", 1)[-1], lo, hi,
                                                   "OK" if ok else "OFFSET from the pivot!"))
    for path, z, name in ((BASE_PATH, 0.0, "RomanPavilion2_Base"),
                          (ARCH_PATH, Z_ARCH0, "RomanPavilion2_Arch"),
                          (DOME_PATH, Z_ARCH1, "RomanPavilion2_Dome")):
        placed += 1 if spawn(path, unreal.Vector(ox, oy, z), name) else 0
    for k in range(N_COL):
        angle = 2.0 * math.pi * k / N_COL
        label = "RomanPavilion2_Column_%02d" % (k + 1)
        location = unreal.Vector(ox + R_COL * math.cos(angle), oy + R_COL * math.sin(angle), V)
        placed += 1 if spawn(COLUMN_PATH, location, label) else 0
    log("placed %d new pavilion actors at (%.0f, %.0f)" % (placed, ox, oy))
    try:
        saved = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    except Exception:
        saved = unreal.EditorLevelLibrary.save_current_level()
    log("level saved: %s (placed %d, expected %d)" % (saved, placed, 3 + N_COL))
else:
    log("probe failed - level left untouched, old pavilion still stands")

bad = [e for e in LOG if e[1] is False]
log("steps=%d failed=%d" % (len(LOG), len(bad)))
log("RESULT: " + ("PASS" if not bad and rib_ok and not coffer_ok and geometry_ok else "CHECK"))
