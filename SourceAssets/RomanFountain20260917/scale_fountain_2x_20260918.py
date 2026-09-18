"""Scale SM_RomanFountain_20 to 2x (960x960x720) WITHOUT ModelingService (this editor session
may not have it): native GeometryScript route -
  copy_mesh_from_static_mesh -> scale_mesh(2,2,2) -> copy_mesh_to_static_mesh,
then complex-as-simple collision (triangle collision scales with the mesh for free; the stored
1x AlignedBoxes are cleared), palette footprint 48x48x36, map actor re-grounded to z=-360.

Runs EITHER via the running editor's remote-exec channel OR headless (editor closed):
  python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/RomanFountain20260917/scale_fountain_2x_20260918.py
  UnrealEditor-Cmd <uproject> -run=pythonscript -script=<abs path> -unattended -NullRHI -nosplash -abslog=<abs log>
"""

import os
import time

import unreal

DIR = "/Game/Props/RomanFountain20260917"
FULL = DIR + "/SM_RomanFountain_20"
PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
LEVEL = "/Game/GameMaps/DayNight_Lighting"
SCALE = 2.0
STARTED = time.time()
LOG = []


def log(m):
    print("[s2x] " + m)


def check(label, ok):
    LOG.append((label, bool(ok)))
    log("%-26s %s" % (label, "OK" if ok else "FAIL"))


def disk(path):
    full = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + \
        path.split("/Game/", 1)[1] + ".uasset"
    if not os.path.exists(full):
        return None
    st = os.stat(full)
    return st.st_size, time.strftime("%H:%M:%S", time.localtime(st.st_mtime)), st.st_mtime


def wait_fresh(path, timeout=25.0):
    end = time.time() + timeout
    while time.time() < end:
        stamp = disk(path)
        if stamp and stamp[2] >= STARTED - 5.0:
            return stamp
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if asset:
            unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(path)], False)
            unreal.EditorAssetLibrary.save_loaded_asset(asset, True)
        time.sleep(2.0)
    return disk(path)


# ---------------------------------------------------------------- 1. geometry scale
mesh = unreal.EditorAssetLibrary.load_asset(FULL)
check("asset_loadable", mesh is not None)
if not mesh:
    raise SystemExit(0)

bb0 = mesh.get_bounds()
log("before: bbox %.0fx%.0fx%.0f origin z=%.1f tris=%d" % (
    bb0.box_extent.x * 2, bb0.box_extent.y * 2, bb0.box_extent.z * 2,
    bb0.origin.z, mesh.get_num_triangles(0)))

already_2x = abs(bb0.box_extent.x * 2 - 960.0) < 0.5 and abs(bb0.box_extent.z * 2 - 720.0) < 0.5
if abs(bb0.box_extent.x * 2 - 480.0) > 0.5 and not already_2x:
    log("ABORT: unexpected mesh size %.0f - refusing to scale (double-scale guard)" % (bb0.box_extent.x * 2))
    raise SystemExit(0)

dm = None
if already_2x:
    log("mesh already 960x960x720 - geometry scale SKIPPED (idempotent rerun)")
else:
    dm = unreal.DynamicMesh()
    from_opts = unreal.GeometryScriptCopyMeshFromAssetOptions()
    read_lod = unreal.GeometryScriptMeshReadLOD()
    dm, outcome = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
        mesh, dm, from_opts, read_lod)
    log("copy_from_static outcome=%s" % outcome)
    check("copy_from_static", dm is not None and "fail" not in str(outcome).lower())

    dm = unreal.GeometryScript_MeshTransforms.scale_mesh(
        dm, unreal.Vector(SCALE, SCALE, SCALE), unreal.Vector(0.0, 0.0, 0.0), True)
    check("scale_mesh_2x", dm is not None)

    to_opts = unreal.GeometryScriptCopyMeshToAssetOptions()
    mat_props = [n for n in dir(to_opts) if "material" in n.lower()]
    log("copy-to-asset material props: %s" % mat_props)
    write_lod = unreal.GeometryScriptMeshWriteLOD()
    _, outcome2 = unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(
        dm, mesh, to_opts, write_lod, True)
    log("copy_to_static outcome=%s" % outcome2)
    check("copy_to_static", "fail" not in str(outcome2).lower())

if not already_2x:
    # stored 1x AlignedBoxes are stale after the overwrite - drop every simple shape, use the
    # (scaled) triangles instead
    setup = mesh.get_editor_property("body_setup")
    if setup:
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
        setup.set_editor_property("collision_trace_flag",
                                  unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        check("collision_complex_as_simple", True)
    check("mesh_saved_disk", bool(wait_fresh(FULL)))
mesh = unreal.load_asset(FULL)
bb1 = mesh.get_bounds()
log("after: bbox %.0fx%.0fx%.0f origin z=%.1f tris=%d slots=%d" % (
    bb1.box_extent.x * 2, bb1.box_extent.y * 2, bb1.box_extent.z * 2,
    bb1.origin.z, mesh.get_num_triangles(0),
    len(mesh.get_editor_property("static_materials"))))
check("bbox_doubled", abs(bb1.box_extent.x * 2 - 960) < 0.5 and
      abs(bb1.box_extent.y * 2 - 960) < 0.5 and abs(bb1.box_extent.z * 2 - 720) < 0.5)
check("materials_kept", len(mesh.get_editor_property("static_materials")) == 2)

# ---------------------------------------------------------------- 3. palette footprint 48x48x36
pal = unreal.EditorAssetLibrary.load_asset(PALETTE)
if pal:
    rebuilt = []
    for e in pal.get_editor_property("components") or []:
        copy = unreal.VoxelBuildPrefab()
        for field in ("id", "display_name", "mesh", "footprint", "surface", "pivot_offset_cm",
                      "actor_class", "actor_offset_cm", "material"):
            copy.set_editor_property(field, e.get_editor_property(field))
        if str(copy.get_editor_property("id")) == "roman_fountain":
            copy.set_editor_property("footprint", unreal.IntVector(48, 48, 36))
        rebuilt.append(copy)
    pal.modify()
    pal.set_editor_property("components", rebuilt)
    unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(PALETTE)], False)
    pstamp = wait_fresh(PALETTE)
    check("palette_footprint_48_48_36", bool(pstamp))
    back = unreal.load_asset(PALETTE)
    for e in (back.get_editor_property("components") or []):
        if str(e.get_editor_property("id")) == "roman_fountain":
            fp = e.get_editor_property("footprint")
            log("palette readback roman_fountain cells %dx%dx%d" % (fp.x, fp.y, fp.z))
else:
    check("palette_loadable", False)

# ---------------------------------------------------------------- 4. map actor re-ground
try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    pie = les.is_in_play_in_editor()
    wpath = ""
    try:
        wpath = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem). \
            get_editor_world().get_path_name() or ""
    except Exception:
        pass
    log("world=%r PIE=%s" % (wpath, pie))
    if pie:
        log("PIE active - level ops skipped")
    else:
        touched = False
        if "DayNight_Lighting" in wpath:
            touched = True   # already open, work in place
        elif les.load_level(LEVEL):
            touched = True
        if touched:
            actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            fountains = [a for a in actor_sub.get_all_level_actors()
                         if a.get_actor_label() == "RomanFountain1"]
            if len(fountains) == 1:
                a = fountains[0]
                loc0 = a.get_actor_location()
                a.set_actor_location(unreal.Vector(loc0.x, loc0.y, -bb1.origin.z), False, True)
                loc = a.get_actor_location()
                log("RomanFountain1 re-grounded (%.0f,%.0f,%.0f)" % (loc.x, loc.y, loc.z))
                check("actor_regrounded", abs(loc.z + 360.0) < 1.0)
            else:
                check("fountain_actor_count_1", False)
            saved = les.save_current_level()
            umap = unreal.Paths.convert_relative_path_to_full(
                unreal.Paths.project_content_dir()) + "GameMaps/DayNight_Lighting.umap"
            st1 = os.stat(umap).st_mtime if os.path.exists(umap) else 0
            check("umap_saved", bool(saved) and st1 >= STARTED - 5.0)
except Exception as exc:  # noqa: BLE001
    log("level section failed: %s" % exc)
    check("level_section", False)

# ---------------------------------------------------------------- 5. Fab water/sound inventory
try:
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    for cls_path, label in (("/Script/Niagara", "NiagaraSystem"), ("/Script/Engine", "SoundWave"),
                            ("/Script/Engine", "SoundCue")):
        assets = reg.get_assets_by_class(unreal.TopLevelAssetPath(cls_path, label), True)
        hits = []
        for a in assets:
            nm = str(a.package_name)
            low = nm.lower()
            if any(k in low for k in ("water", "waterfall", "river", "stream", "splash",
                                      "fountain", "creek", "brook", "ocean", "lake", "flow",
                                      "droplet", "drip")):
                hits.append(nm)
        log("FAB %s water-ish=%d" % (label, len(hits)))
        for h in hits[:60]:
            log("    " + h)
except Exception as exc:  # noqa: BLE001
    log("fab inventory failed: %s" % exc)

bad = [x for x in LOG if x[1] is False]
log("checks=%d failed=%d %s" % (len(LOG), len(bad), [b[0] for b in bad]))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
