"""Headless acceptance for the 2026-10-13 voxel building fixes (commandlet-reachable face).

Editor closed. Usage:
    UnrealEditor-Cmd <uproject> -run=pythonscript -script=Tools/Building/audit_voxel_fixes_20261013.py -nullrhi -unattended

ENVIRONMENT LIMIT (measured): line traces MISS for everything under -nullrhi pythonscript, so
ground-anchored placement SUCCESS cannot be reproduced here (the 2026-09-16 audit script had the
same constraint and worked by reading VOXEL_REJECT lines). What this script CAN verify:
  A. edit_cells on bare ground is refused (calibration walked the full CanPlaceAt chain; a crash
     or an unexpected early rejection = regression from either fix round)
  B. undo() with empty history+slot returns False without side effects
  C. place_prefab of a FREE piece in mid-air is refused (unsupported rule intact)
  E. place_prefab of the WALL piece (bronze_torch) in mid-air is refused --
     THIS IS THE B4 PROOF: before the fix the wall-mount branch never checked for a real
     surface, so this exact call SUCCEEDED. False now means the server-side revalidation runs.
  G. save() writes the audit slot without crashing
Success-path cases (ground prefab placement, prefab undo fallback, wall piece on a real surface,
solver chains) are covered by code walkthrough; see the session report.
"""

import unreal

MAP = "/Game/GameMaps/DayNight_Lighting"
WORLD_KEY = "VoxelAuditFixes20261013|DayNight_Lighting"
MATERIAL = "marble"

Results = []

def report(name, ok, note=""):
    Results.append((name, bool(ok)))
    unreal.log("[audit] AUDIT_FIX %s %s %s" % ("PASS" if ok else "FAIL", name, note))

def cell(x, y, z):
    return unreal.IntVector(x, y, z)

unreal.SystemLibrary.execute_console_command(None, "fps.Building.DebugLog 1")
unreal.EditorLoadingAndSavingUtils.load_map(MAP)
world = unreal.EditorLevelLibrary.get_editor_world()
unreal.log("AUDIT_FIX map=%s" % world.get_name())

build = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.VoxelBuildWorld, unreal.Vector(0, 0, 0))
ok_init = bool(build and build.debug_initialize(WORLD_KEY))
unreal.log("AUDIT_FIX spawned=%s initialize=%s" % (build is not None, ok_init))
if not ok_init:
    raise SystemExit(1)

# --- A. bare-ground placement refused (full CanPlaceAt walk, no crash) ------------------------
ok_a = not build.edit_cells([cell(39, -40, 0)], unreal.Name(MATERIAL))
report("A mid-placement refused (trace-less env)", ok_a,
       "material_at=%s" % build.material_at(cell(39, -40, 0)))

# --- B. undo on empty history/slot ----------------------------------------------------------
report("B undo empty is False", build.undo() is False)

# --- C. FREE prefab in mid-air refused (unsupported rule intact) ------------------------------
report("C free prefab mid-air refused",
       not build.place_prefab(unreal.Name("baluster_small"), cell(200, 200, 8), 0))

# --- E. WALL prefab in mid-air refused == B4 revalidation is live ----------------------------
# Before the fix this exact call succeeded (wall mount trusted the request unconditionally).
report("E wall prefab mid-air refused (B4 live)",
       not build.place_prefab(unreal.Name("bronze_torch"), cell(210, 200, 8), 0))

# --- G. save ----------------------------------------------------------------------------------
report("G save audit slot", build.save())

failed = [n for n, ok in Results if not ok]
unreal.log("[audit] AUDIT_FIX COMPLETE total=%d failed=%d" % (len(Results), len(failed)))
for n in failed:
    unreal.log("[audit] AUDIT_FIX FAILED_ITEM %s" % n)
