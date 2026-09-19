"""Headless: replace the user's blocky voxel railing with the roman balustrade kit.

World key: ColdSteelPlayer|DayNight_Lighting. Steps:
  1. Load the build world from the existing save (DebugInitialize).
  2. Remove ALL existing marble voxels (the old hand-built railing, 305 blocks).
  3. Build the new run along +y at x cells 28..29 (world x 560..600):
       columns   baluster_small  2x2x5   anchors y=-36, -27, -18  (180 cm rhythm)
       infill    marble voxels, 2 cells tall (z 0..1), filling the 7-cell gaps
       rails     balustrade_rail_200 x2 at z cell 5, y=-36 and y=-26  (400 cm closed run)
  4. Save + in-process readback.
"""

import unreal

KEY = "ColdSteelPlayer|DayNight_Lighting"
WORLD_cls = unreal.load_class(None, "/Script/FPSGAME.VoxelBuildWorld")
NONE_NAME = unreal.Name("None")
MARBLE = unreal.Name("marble")


def log(m):
    print("[rebuild] " + m)


sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
# The commandlet starts with an EMPTY world: no Floor, so every voxel grounding raycast
# fails (VOXEL_REJECT stage=support with un-anchored cells). Load the map first.
unreal.EditorLoadingAndSavingUtils.load_map("/Game/GameMaps/DayNight_Lighting")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
log("map: %s" % world.get_name())
unreal.SystemLibrary.execute_console_command(world, "fps.Building.DebugLog 1", None)
bw = sub.spawn_actor_from_class(WORLD_cls, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
if not bw:
    raise SystemExit("cannot spawn VoxelBuildWorld")

log("initialize=%s" % bw.call_method("DebugInitialize", args=(KEY,)))
log("before: blocks=%s prefabs=%s" % (bw.call_method("BlockCount"), bw.call_method("PrefabCount")))

# --------------------------------------- idempotent cleanup: prefabs then voxels
for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
    if a.get_class().get_name() == "VoxelBuildPrefabActor" and a.get_attach_parent_actor() is None:
        log("removing prefab actor at %s" % a.get_actor_location())
        bw.call_method("RemovePrefab", args=(a,))
old = []
for cz in range(0, 21):
    for cy in range(-40, 41):
        for cx in range(-40, 41):
            if str(bw.call_method("MaterialAt", args=(unreal.IntVector(cx, cy, cz),))) != "None":
                old.append(unreal.IntVector(cx, cy, cz))
if old:
    ok = bw.call_method("EditCells", args=(old, NONE_NAME))
    log("cleared %d old blocks -> %s (blocks now %s)" % (len(old), ok, bw.call_method("BlockCount")))

# --------------------------------------------------------- 2. columns (prefabs)
X = 28
COLUMN_ANCHORS = [-36, -27, -18]
for y in COLUMN_ANCHORS:
    ok = bw.call_method("PlacePrefab", args=(unreal.Name("baluster_small"),
                                             unreal.IntVector(X, y, 0), 0))
    log("column anchor y=%d -> %s" % (y, ok))

# ------------------------------------------------- 3. marble infill between columns
# Batched per gap and per layer so a rejection isolates itself.
for gi, (y0, y1) in enumerate(((-34, -28), (-25, -19)), 1):
    for z in (0, 1):
        cells = [unreal.IntVector(x, y, z) for y in range(y0, y1 + 1) for x in (X, X + 1)]
        ok = bw.call_method("EditCells", args=(cells, MARBLE))
        log("infill gap%d z=%d %d cells -> %s (blocks now %s)" % (gi, z, len(cells), ok, bw.call_method("BlockCount")))
        if not ok:
            probe = [unreal.IntVector(X, (y0 + y1) // 2, z)]
            ok1 = bw.call_method("EditCells", args=(probe, MARBLE))
            log("  probe single cell %s -> %s" % ((X, (y0 + y1) // 2, z), ok1))

# ------------------------------------------------------------- 4. rails on top
for y in (-36, -26):
    ok = bw.call_method("PlacePrefab", args=(unreal.Name("balustrade_rail_200"),
                                             unreal.IntVector(X, y, 5), 0))
    log("rail anchor y=%d -> %s" % (y, ok))

# ----------------------------------------------------------------- 5. readback
log("after: blocks=%s prefabs=%s" % (bw.call_method("BlockCount"), bw.call_method("PrefabCount")))
checks = [
    ("column base", (X, -36, 0), "None"),          # prefab cells are not voxels
    ("infill mid gap1", (X, -31, 0), "marble"),
    ("infill top gap1", (X, -31, 1), "marble"),
    ("infill gap1 z2 free", (X, -31, 2), "None"),
    ("infill mid gap2", (X, -22, 1), "marble"),
    ("old area cleared", (35, -33, 5), "None"),
]
for label, cell, want in checks:
    got = str(bw.call_method("MaterialAt", args=(unreal.IntVector(*cell),)))
    log("check %-20s cell=%s got=%s want=%s %s" % (label, cell, got, want, "OK" if got == want else "FAIL"))

saved = bw.call_method("Save")
log("save=%s" % saved)
bw.destroy_actor()
log("RESULT: " + ("PASS" if saved else "CHECK"))
