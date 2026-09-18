"""Cake-tier Roman fountain (SM_RomanFountain_20) — stacked-basin "wedding cake" tower.

Eleven independent shells, NO self_union anywhere (the bTrimFlaps pit flattens arcs, and
tangent stacked shells must simply overlap):
  8 marble revolve bodies (material_id 0)  +  3 bowl-filling water bodies (material_id 1 -> slot 1).

Water v2 (user rejected the floating 4 cm discs): each water body is a revolve of the bowl
cavity's cross-section from the floor up to the waterline, with its side boundary pushed
1 cm INTO the marble wall (every side face buried in the opaque solid -> no air gap under the
water, no coplanar z-fighting) and its bottom 1.5 cm into the bowl floor. Only the surface
plane is exposed; it meets the wall in a clean waterline.

Dimensions, cm, everything on the 20 cm build grid:
  step0   r240  z   0.. 10   (10 cm step: a 20 cm edge sits at the character step limit)
  step1   r220  z   6.. 20   (each piece sinks 4 into the one below - coplanar faces z-fight)
  basin0  r206  z  16.. 82   bowl floor 44, water 54..58 (r140, wall >= 158 at those z)
  ped1    r 84  z  40..162   turned shaft through the water up to the middle tier
  basin1  r134  z 158..214   bowl floor 184, water 196..200 (r 92, wall >= 98)
  ped2    r 62  z 180..240
  basin2  r 91  z 236..286   bowl floor 266, water 276..280 (r 58, wall >= 64)
  pigna   r 32  z 262..360   pinecone finial (Fontana della Pigna silhouette), top = 360
  bbox 480 x 480 x 360 -> footprint 24 x 24 x 18 cells, EXACT per axis.

Dispatch HEADLESS (editor closed; a second UnrealEditor-Cmd may not coexist with a running
editor, and the editor's asset lock would swallow the saves):
  "E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" D:/FPS3D/FPSGAME/FPSGAME.uproject \
      -run=pythonscript -script=D:/FPS3D/FPSGAME/SourceAssets/RomanFountain20260917/build_fountain_20260917.py \
      -unattended -NullRHI -nosplash -abslog=D:/FPS3D/FPSGAME/Saved/Logs/fountain_build.log

Order matters: asset + palette writes happen BEFORE load_map (a loaded level makes the palette
save silently fail in the same process). Level placement runs last; headless physics cannot
answer for level geometry, so ground support is checked against actor bounds, not raycasts.
"""

import os
import time

import unreal

SV = unreal.ModelingService
DIR = "/Game/Props/RomanFountain20260917"
FULL = DIR + "/SM_RomanFountain_20"
MARBLE = "/Game/Props/RomanColumn20260915/M_RomanStone_V2"
WATER = "/Game/WaterMaterials/Materials/M_Water_Clean"
PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
STEPS = 96
# 2026-09-18: user asked to stretch the fountain to double size. Every profile coordinate is
# multiplied by SCALE, so the 1x model is recoverable by setting SCALE back to 1.0 and rerunning.
# 2x -> bbox 960x960x720 (still exact 20 cm multiples) -> footprint 48x48x36 cells.
SCALE = 2.0
STARTED = time.time()
LOG = []


def log(m):
    print("[fnt] " + m)


def do(label, result):
    ok = getattr(result, "success", None)
    LOG.append((label, ok))
    log("%-22s %s %s" % (label, ok, getattr(result, "message", "") or ""))
    return ok


def tf(x=0.0, y=0.0, z=0.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(0.0, 0.0, 0.0).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def v2(radius, height):
    return unreal.Vector2D(radius, height)


def disk(path):
    full = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + \
        path.split("/Game/", 1)[1] + ".uasset"
    if not os.path.exists(full):
        return None
    st = os.stat(full)
    return st.st_size, time.strftime("%H:%M:%S", time.localtime(st.st_mtime)), st.st_mtime


def collision_summary(path):
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    setup = mesh.get_editor_property("body_setup") if mesh else None
    agg = None
    if setup:
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


def strip_stray_shapes(path):
    """The generators bolt a sphere/sphyl/taper onto round meshes; the dome's capsule once
    plugged the whole pavilion. Every shell here is a closed solid, so a box per shell from
    AlignedBoxes is the collision we want; anything else goes."""
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    setup = mesh.get_editor_property("body_setup") if mesh else None
    if not setup:
        return {}
    for prop in ("agg_geom", "aggregate_geometry"):
        try:
            agg = setup.get_editor_property(prop)
        except Exception:
            continue
        if not agg:
            continue
        for elem in ("sphere_elems", "sphyl_elems", "taper_elems", "convex_elems"):
            try:
                agg.set_editor_property(elem, [])
            except Exception:
                pass
        break
    unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(path)], False)
    return collision_summary(path)


# ------------------------------------------------------------------ profile data
PROFILES = {
    "step0": [(0, 0), (240, 0), (240, 10), (0, 10)],
    "step1": [(0, 6), (220, 6), (220, 20), (0, 20)],
    "basin0": [(0, 16), (192, 16), (200, 20), (200, 30), (193, 34), (196, 44), (206, 58),
               (206, 66), (198, 74), (202, 78), (196, 82), (186, 80), (178, 70), (166, 60),
               (150, 52), (120, 46), (0, 44)],
    "ped1": [(0, 40), (84, 40), (84, 52), (76, 52), (70, 58), (66, 62), (72, 68), (64, 76),
             (60, 80), (58, 120), (56, 132), (62, 138), (62, 142), (58, 146), (68, 152),
             (76, 156), (76, 162), (0, 162)],
    "basin1": [(0, 158), (124, 158), (130, 162), (130, 172), (124, 175), (127, 183),
               (134, 196), (134, 202), (128, 208), (131, 212), (124, 214), (114, 212),
               (108, 204), (98, 196), (84, 190), (64, 186), (0, 184)],
    "ped2": [(0, 180), (62, 180), (62, 190), (54, 190), (48, 196), (44, 202), (40, 208),
             (38, 222), (42, 228), (42, 232), (50, 236), (52, 240), (0, 240)],
    "basin2": [(0, 236), (84, 236), (88, 240), (88, 250), (83, 253), (86, 261), (91, 272),
               (91, 276), (85, 282), (87, 286), (80, 286), (72, 282), (64, 276), (52, 271),
               (38, 268), (0, 266)],
    "pigna": [(0, 262), (32, 262), (32, 266), (28, 268), (30, 272), (24, 276), (31, 282),
              (24, 286), (29, 292), (22, 296), (27, 302), (19, 306), (23, 312), (16, 316),
              (19, 322), (13, 326), (15, 332), (10, 336), (11, 341), (8, 344), (10, 348),
              (6, 350), (14, 354), (15, 358), (9, 360), (0, 360)],
}
WATER_BODIES = [
    # v3 (user still read the v2 water as floating): waterlines raised to ~8 cm below each rim
    # (74/206/282 vs 58/200/280) so the water visually joins rim and pedestal, and the material
    # switched to the project's OPAQUE water (a low-opacity "glass sheet" over the visible bowl
    # floor is exactly what read as a hovering disc). Side boundary stays 1 cm INSIDE the
    # marble wall, bottom 1.5 below the floor: only the surface plane is exposed.
    # wall r at z: (120,46)(150,52)(166,60)(178,70)(186,80) -> +1 cm each
    [(0, 42.5), (121, 42.5), (121, 46), (151, 52), (163, 58), (174, 66), (182.2, 74), (0, 74)],
    # wall: (64,186)(84,190)(98,196)(108,204)(114,212) -> +1
    [(0, 182.5), (65, 182.5), (65, 186), (85, 190), (99, 196), (109, 204), (110.5, 206), (0, 206)],
    # wall: (38,268)(52,271)(64,276)(72,282) -> +1
    [(0, 264.5), (39, 264.5), (39, 268), (53, 271), (65, 276), (73, 282), (0, 282)],
]


def pick_water_material():
    """Opaque water kills the see-through 'glass disc' read; Clean is the fallback."""
    for cand in ("/Game/WaterMaterials/Materials/M_Water_Opaque",
                 "/Game/WaterMaterials/Materials/M_Water_Clean"):
        if unreal.load_asset(cand):
            log("water material: %s" % cand)
            return cand
    log("no water material loadable!")
    LOG.append(("water_material_loadable", False))
    return WATER

# ------------------------------------------------------------------ build
f = SV.create_mesh().handle
for name, prof in PROFILES.items():
    r = SV.append_revolve_polygon(f, tf(), [v2(x * SCALE, z * SCALE) for (x, z) in prof],
                                  0.0, STEPS, 360.0, 0)
    log("revolve %-8s %s" % (name, r.success))
for wi, wprof in enumerate(WATER_BODIES):
    r = SV.append_revolve_polygon(f, tf(), [v2(x * SCALE, z * SCALE) for (x, z) in wprof],
                                  0.0, STEPS, 360.0, 1)
    log("water   fill%d   %s" % (wi, r.success))

BB_XY = 480.0 * SCALE
BB_Z = 360.0 * SCALE
CELLS = (int(round(BB_XY / 20.0)), int(round(BB_XY / 20.0)), int(round(BB_Z / 20.0)))
info = SV.get_mesh_info(f)
bb = (info.bounds_max.x - info.bounds_min.x, info.bounds_max.y - info.bounds_min.y,
      info.bounds_max.z - info.bounds_min.z)
ok_geom = (info.open_border_edges == 0 and info.connected_components == 11 and
           abs(bb[0] - BB_XY) < 1.0 and abs(bb[1] - BB_XY) < 1.0 and abs(bb[2] - BB_Z) < 1.0)
log("mesh: tris=%d comps=%d (want 11) open=%d (want 0) bbox %.0f x %.0f x %.0f  z %.1f..%.1f -> %s" % (
    info.triangle_count, info.connected_components, info.open_border_edges,
    bb[0], bb[1], bb[2], info.bounds_min.z, info.bounds_max.z,
    "OK" if ok_geom else "MISMATCH"))
LOG.append(("geometry", ok_geom))

do("uv", SV.auto_uv(f, "XAtlas", 0))
do("save", SV.save_mesh_to_static_mesh(f, FULL, True, True, False, True))
SV.release_mesh(f)

asset = None
for _ in range(40):
    asset = unreal.EditorAssetLibrary.load_asset(FULL)
    if asset:
        break
    time.sleep(0.25)
log("asset loadable: %s" % bool(asset))

stamp = disk(FULL)
fresh = bool(stamp and stamp[2] >= STARTED - 5.0)
for attempt in range(4):
    if fresh:
        break
    log("disk STALE, retry %d in 4 s" % (attempt + 1))
    time.sleep(4.0)
    if asset:
        unreal.EditorAssetLibrary.save_loaded_asset(asset, True)
    stamp = disk(FULL)
    fresh = bool(stamp and stamp[2] >= STARTED - 5.0)
LOG.append(("disk", fresh))
log("disk %s %s" % ("%d B / %s" % (stamp[0], stamp[1]) if stamp else "MISSING",
                    "FRESH" if fresh else "STALE"))

if asset:
    do("collision", SV.generate_collision(FULL, "AlignedBoxes", 1, 25, True))
    counts = collision_summary(FULL)
    log("collision raw: %s" % counts)
    if any(counts.get(k) for k in ("sphere", "sphyl", "taper", "convex")):
        counts = strip_stray_shapes(FULL)
        log("collision stripped: %s" % counts)
    clean = bool(counts.get("box")) and not any(counts.get(k) for k in ("sphere", "sphyl", "taper", "convex"))
    LOG.append(("collision_clean", clean))

    do("materials", SV.set_asset_materials(FULL, MARBLE + "," + pick_water_material(), True))
    try:
        slots = asset.get_editor_property("static_materials")
        mats = []
        for i in range(len(slots)):
            m = None
            for attr in (lambda: asset.get_material(i), lambda: slots[i].get_editor_property("material")):
                try:
                    m = attr()
                    if m:
                        break
                except Exception:
                    continue
            mats.append(str(m.get_path_name() if m else "?"))
        log("slots: %d -> %s" % (len(slots), mats))
        LOG.append(("slot1_water", "Water" in mats[-1] if mats else False))
        LOG.append(("slot0_marble", "RomanStone" in mats[0] if mats else False))
    except Exception as exc:  # noqa: BLE001
        log("slot readback failed (non-fatal): %s" % exc)

    bb2 = asset.get_bounds()
    log("asset bbox %.0f x %.0f x %.0f origin (%.1f, %.1f, %.1f) tris=%d" % (
        bb2.box_extent.x * 2, bb2.box_extent.y * 2, bb2.box_extent.z * 2,
        bb2.origin.x, bb2.origin.y, bb2.origin.z, asset.get_num_triangles(0)))

# ------------------------------------------------------------------ palette entry
pal = unreal.EditorAssetLibrary.load_asset(PALETTE)
if not pal:
    log("palette NOT loadable - abort palette write")
    LOG.append(("palette_load", False))
else:
    rebuilt = []
    for e in pal.get_editor_property("components") or []:
        copy = unreal.VoxelBuildPrefab()
        for field in ("id", "display_name", "mesh", "footprint", "surface", "pivot_offset_cm",
                      "actor_class", "actor_offset_cm", "material"):
            copy.set_editor_property(field, e.get_editor_property(field))
        if str(copy.get_editor_property("id")) != "roman_fountain":
            rebuilt.append(copy)
    stone = unreal.EditorAssetLibrary.load_asset(MARBLE)
    entry = unreal.VoxelBuildPrefab()
    entry.set_editor_property("id", "roman_fountain")
    entry.set_editor_property("display_name", unreal.Text("罗马喷泉（蛋糕塔）"))
    entry.set_editor_property("mesh", asset)
    entry.set_editor_property("footprint", unreal.IntVector(CELLS[0], CELLS[1], CELLS[2]))
    entry.set_editor_property("surface", stone)
    entry.set_editor_property("pivot_offset_cm", unreal.Vector(0.0, 0.0, 0.0))
    entry.set_editor_property("material", unreal.Name("marble"))
    rebuilt.append(entry)
    pal.modify()
    pal.set_editor_property("components", rebuilt)
    save_ok = unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(PALETTE)], False)
    LOG.append(("palette_saved", bool(save_ok)))
    pstamp = disk(PALETTE)
    pfresh = bool(pstamp and pstamp[2] >= STARTED - 5.0)
    LOG.append(("palette_disk", pfresh))
    log("palette save=%s disk %s %s" % (
        save_ok, "%d B / %s" % (pstamp[0], pstamp[1]) if pstamp else "missing",
        "FRESH" if pfresh else "STALE"))
    back = unreal.load_asset(PALETTE)
    entries = back.get_editor_property("components") or []
    log("palette read-back: %d entries" % len(entries))
    for e in entries:
        fp = e.get_editor_property("footprint")
        log("  %-24s cells %2dx%2dx%-2d group=%-7s" % (
            str(e.get_editor_property("id")), fp.x, fp.y, fp.z,
            str(e.get_editor_property("material"))))

# ------------------------------------------------------------------ OBJ dump for offline forensics
try:
    loaded = SV.load_mesh_from_static_mesh(FULL, 0)
    fh = getattr(loaded, "handle", None)
    if fh and fh >= 0:
        dm = SV.get_dynamic_mesh(fh)
        _, tlist, _ = dm.get_all_triangle_i_ds()
        out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forensic_fountain.obj")
        verts = {}
        order = []
        with open(out_path, "w") as fp:
            fp.write("# fountain forensic dump\n")
            for tid in tlist.convert_index_list_to_array():
                ok, v1, v2_, v3 = dm.get_triangle_positions(int(tid))
                if not ok:
                    continue
                idx = []
                for p in (v1, v2_, v3):
                    key = (round(p.x, 4), round(p.y, 4), round(p.z, 4))
                    if key not in verts:
                        verts[key] = len(verts) + 1
                        order.append("v %.4f %.4f %.4f" % key)
                    idx.append(verts[key])
                fp.write("f %d %d %d\n" % tuple(idx))
            fp.write("\n".join(order) + "\n")
        SV.release_mesh(fh)
        log("forensic obj: %s (%d verts)" % (out_path, len(verts)))
    else:
        log("forensic: reload failed (%s)" % getattr(loaded, "message", ""))
except Exception as exc:  # noqa: BLE001
    log("forensic dump failed: %s" % exc)

# ------------------------------------------------------------------ level placement
LEVEL = "/Game/GameMaps/DayNight_Lighting"
FOOT = BB_XY
HEIGHT = BB_Z
CANDIDATES = [(1350.0, -1150.0), (2400.0, 600.0), (1350.0, 350.0)]


def aabb(actor):
    origin, extent = actor.get_actor_bounds(False)
    return (origin.x - extent.x, origin.x + extent.x, origin.y - extent.y,
            origin.y + extent.y, origin.z - extent.z, origin.z + extent.z)


try:
    umap_full = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + \
        "GameMaps/DayNight_Lighting.umap"
    st0 = os.stat(umap_full).st_mtime if os.path.exists(umap_full) else 0

    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    headless = os.environ.get("FOUNTAIN_HEADLESS") == "1"
    pie = False
    wpath = ""
    if headless:
        log("headless mode - skipping PIE/world queries")
        # headless commandlet starts with no level loaded; load it explicitly below
    else:
        try:
            pie = les.is_in_play_in_editor()
        except Exception:
            pie = False
        try:
            sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            wpath = sub.get_editor_world().get_path_name() or "" if sub else ""
        except Exception:
            pass
    log("editor world=%r PIE=%s headless=%s" % (wpath, pie, headless))
    if pie:
        log("PIE active - level edits SKIPPED (asset+palette still written); rerun after PIE stops")
    elif headless or "DayNight_Lighting" in wpath or les.load_level(LEVEL):
        # headless starts with no level and must load it; an already-open level is NOT reloaded
        # (load_level would discard the user's unsaved edits)
        actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        all_actors = actor_sub.get_all_level_actors()
        solids = [a for a in all_actors if a.get_class().get_name() == "StaticMeshActor"]
        boxes = {a: aabb(a) for a in solids}

        existing = [a for a in all_actors if a.get_actor_label() == "RomanFountain1"]
        placed = None
        if existing:
            # rerun: refresh the mesh reference in place, never spawn a duplicate; re-ground the
            # actor because the scaled mesh's bounds origin moved (1x placed z=-180, 2x needs -360)
            actor = existing[0]
            mesh = unreal.EditorAssetLibrary.load_asset(FULL)
            bb3 = mesh.get_bounds()
            smc = actor.get_component_by_class(unreal.StaticMeshComponent)
            smc.set_mobility(unreal.ComponentMobility.MOVABLE)
            smc.set_static_mesh(mesh)
            loc0 = actor.get_actor_location()
            actor.set_actor_location(unreal.Vector(loc0.x, loc0.y, -bb3.origin.z), False, True)
            loc = actor.get_actor_location()
            log("RomanFountain1 re-grounded at (%.0f,%.0f,%.0f) - mesh refreshed, %.0fx scale" % (
                loc.x, loc.y, loc.z, SCALE))
        else:
            for (cx, cy) in CANDIDATES:
                span = (cx - FOOT / 2, cx + FOOT / 2, cy - FOOT / 2, cy + FOOT / 2, 0.0, HEIGHT)
                # ground: a static mesh actor whose top is at z ~ 0 and whose x/y span covers the site
                ground = None
                for a, b in boxes.items():
                    if (b[4] <= -5.0 and -1.0 <= b[5] <= 5.0 and
                            b[0] <= span[0] and b[1] >= span[1] and b[2] <= span[2] and b[3] >= span[3]):
                        ground = a
                        break
                if not ground:
                    log("candidate (%.0f,%.0f): no ground cover" % (cx, cy))
                    continue
                clash = None
                for a, b in boxes.items():
                    if a is ground:
                        continue
                    if (b[0] < span[1] and b[1] > span[0] and b[2] < span[3] and
                            b[3] > span[2] and b[4] < span[5] and b[5] > span[4]):
                        clash = a.get_name()
                        break
                if clash:
                    log("candidate (%.0f,%.0f): blocked by %s" % (cx, cy, clash))
                    continue
                placed = (cx, cy, ground)
                break

            if not placed:
                log("NO CLEAR CANDIDATE - fountain not placed")
                LOG.append(("placement", False))
            else:
                cx, cy, ground = placed
                mesh = unreal.EditorAssetLibrary.load_asset(FULL)
                bb3 = mesh.get_bounds()
                loc = unreal.Vector(cx, cy, -bb3.origin.z)
                actor = actor_sub.spawn_actor_from_class(unreal.StaticMeshActor, loc, unreal.Rotator(0, 0, 0))
                if not actor:
                    log("spawn FAILED (headless spawn path broken?)")
                    LOG.append(("placement", False))
                else:
                    smc = actor.get_component_by_class(unreal.StaticMeshComponent)
                    smc.set_mobility(unreal.ComponentMobility.MOVABLE)
                    smc.set_static_mesh(mesh)
                    actor.set_actor_label("RomanFountain1")
                    log("placed RomanFountain1 at (%.0f,%.0f,%.0f) on %s" % (
                        cx, cy, loc.z, ground.get_name()))

        # both paths converge here: the level must be saved either way
        saved = les.save_current_level()
        st1 = os.stat(umap_full).st_mtime if os.path.exists(umap_full) else 0
        LOG.append(("umap_saved", bool(saved) and st1 > st0))
        log("save_current_level=%s umap mtime %s -> %s" % (
            saved, "FRESH" if st1 > st0 else "STALE", time.strftime("%H:%M:%S", time.localtime(st1))))
except Exception as exc:  # noqa: BLE001
    log("level section failed: %s" % exc)
    LOG.append(("level_section", False))

bad = [x for x in LOG if x[1] is False]
log("checks=%d failed=%d %s" % (len(LOG), len(bad), [b[0] for b in bad]))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
