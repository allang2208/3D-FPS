"""Fix the REAL 'floating' cause: the middle tier cantilevers over the 8.2 m water disc on a
2.4 m shaft that sits fully in shadow, so the tower reads as hovering. Add a socle that rises
OUT of the water: base ring r208 (z 84..112) + tapered drum r196->r156 (z 112..248). The
waterline (z=148) then crosses the drum at r~182, giving a visible waterline circle and a
massive stone support under the overhang. Native GeometryScript route (works in the running
editor; no ModelingService). New shells are opaque marble overlapping the water body - the
water plane inside them is hidden, the intersection line is the waterline."""

import os
import time

import unreal

FULL = "/Game/Props/RomanFountain20260917/SM_RomanFountain_20"
STARTED = time.time()
LOG = []


def log(m):
    print("[soc] " + m)


def check(label, ok):
    LOG.append((label, bool(ok)))
    log("%-24s %s" % (label, "OK" if ok else "FAIL"))


def disk(path):
    full = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + \
        path.split("/Game/", 1)[1] + ".uasset"
    st = os.stat(full)
    return st.st_size, st.st_mtime


mesh = unreal.EditorAssetLibrary.load_asset(FULL)
check("asset_loadable", mesh is not None)
if not mesh:
    raise SystemExit(0)
size0, mtime0 = disk(FULL)

dm = unreal.DynamicMesh()
dm, outcome = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
    mesh, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
log("copy_from: %s" % outcome)

opts = unreal.GeometryScriptPrimitiveOptions()
tf_ring = unreal.Transform()
tf_ring.translation = unreal.Vector(0.0, 0.0, 84.0)
unreal.GeometryScript_Primitives.append_cylinder(dm, opts, tf_ring, 208.0, 28.0, 96, 0, True,
                                                 unreal.GeometryScriptPrimitiveOriginMode.BASE)
tf_cone = unreal.Transform()
tf_cone.translation = unreal.Vector(0.0, 0.0, 112.0)
unreal.GeometryScript_Primitives.append_cone(dm, opts, tf_cone, 196.0, 156.0, 136.0, 96, 4, True,
                                             unreal.GeometryScriptPrimitiveOriginMode.BASE)
log("socle appended: ring r208 z84..112, drum r196->r156 z112..248")

_, outcome2 = unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(
    dm, mesh, unreal.GeometryScriptCopyMeshToAssetOptions(), unreal.GeometryScriptMeshWriteLOD(), True)
log("copy_to: %s" % outcome2)

unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(FULL)], False)
unreal.EditorAssetLibrary.save_loaded_asset(mesh, True)
stamp = None
for _ in range(15):
    stamp = disk(FULL)
    if stamp[1] > mtime0:
        break
    time.sleep(2.0)
    unreal.EditorAssetLibrary.save_loaded_asset(mesh, True)
check("saved_to_disk", stamp[1] > mtime0)
log("disk %d B (was %d)" % (stamp[0], size0))

mesh2 = unreal.load_asset(FULL)
bb = mesh2.get_bounds()
check("bbox_still_960x960x720",
      abs(bb.box_extent.x * 2 - 960) < 1.0 and abs(bb.box_extent.z * 2 - 720) < 1.0)
check("slots_still_2", len(mesh2.get_editor_property("static_materials")) == 2)
log("tris=%d (socle added ~%d)" % (mesh2.get_num_triangles(0), mesh2.get_num_triangles(0) - 22272))

# re-ground the placed actor in case bounds shifted (they should not have)
try:
    headless = os.environ.get("FOUNTAIN_HEADLESS") == "1"
    sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    w = sub.get_editor_world() if sub else None
    if not headless and w and "DayNight_Lighting" in (w.get_path_name() or ""):
        actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        fs = [a for a in actor_sub.get_all_level_actors() if a.get_actor_label() == "RomanFountain1"]
        if len(fs) == 1 and abs(fs[0].get_actor_location().z + 360.0) > 1.0:
            loc0 = fs[0].get_actor_location()
            fs[0].set_actor_location(unreal.Vector(loc0.x, loc0.y, -bb.origin.z), False, True)
            log("actor re-grounded to z=%.0f" % fs[0].get_actor_location().z)
        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if les and not les.is_in_play_in_editor():
            ok = les.save_current_level()
            log("level save=%s" % ok)
            check("level_saved", ok)
        else:
            log("PIE on - level save skipped (asset itself is saved)")
    elif headless:
        log("headless - level untouched (asset saved; actor needs no reground, bounds unchanged)")
except Exception as exc:  # noqa: BLE001
    log("level touch skipped: %s" % exc)

bad = [x for x in LOG if x[1] is False]
log("checks=%d failed=%d %s" % (len(LOG), len(bad), [b[0] for b in bad]))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
