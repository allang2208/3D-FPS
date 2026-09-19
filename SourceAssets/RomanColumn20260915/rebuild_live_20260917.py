"""Run INSIDE the live editor: rebuild the railing in the user's ACTIVE build world.

Finds the VoxelBuildWorld in the PIE game world, then applies the same idempotent rebuild as
rebuild_railing_20260917.py (columns + marble infill + rails). Autosave persists it.
"""

import unreal

NONE_NAME = unreal.Name("None")
MARBLE = unreal.Name("marble")


def log(m):
    print("[live] " + m)


les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
log("pie=%s" % les.is_in_play_in_editor())
gw = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if not gw:
    log("NO PIE world - user not in build mode")
    raise SystemExit("no game world")

log("game world: %s" % gw.get_name())
bw = None
for a in unreal.GameplayStatics.get_all_actors_of_class(gw, unreal.Actor):
    if a.get_class().get_name() == "VoxelBuildWorld":
        bw = a
        break
if not bw:
    log("no live VoxelBuildWorld actor in game world")
    raise SystemExit("no build world")

unreal.SystemLibrary.execute_console_command(gw, "fps.Building.DebugLog 1", None)
log("live world found: blocks=%s prefabs=%s" % (bw.call_method("BlockCount"), bw.call_method("PrefabCount")))

# idempotent cleanup
for a in unreal.GameplayStatics.get_all_actors_of_class(gw, unreal.Actor):
    if a.get_class().get_name() == "VoxelBuildPrefabActor":
        log("removing prefab at %s" % a.get_actor_location())
        bw.call_method("RemovePrefab", args=(a,))
old = []
for cz in range(0, 21):
    for cy in range(-40, 41):
        for cx in range(-40, 41):
            if str(bw.call_method("MaterialAt", args=(unreal.IntVector(cx, cy, cz),))) != "None":
                old.append(unreal.IntVector(cx, cy, cz))
if old:
    log("clearing %d old blocks -> %s" % (len(old), bw.call_method("EditCells", args=(old, NONE_NAME))))

X = 28
for y in (-36, -27, -18):
    ok = bw.call_method("PlacePrefab", args=(unreal.Name("baluster_small"), unreal.IntVector(X, y, 0), 0))
    log("column y=%d -> %s" % (y, ok))

for gi, (y0, y1) in enumerate(((-34, -28), (-25, -19)), 1):
    for z in (0, 1):
        cells = [unreal.IntVector(x, y, z) for y in range(y0, y1 + 1) for x in (X, X + 1)]
        ok = bw.call_method("EditCells", args=(cells, MARBLE))
        log("infill gap%d z=%d -> %s (blocks=%s)" % (gi, z, ok, bw.call_method("BlockCount")))

for y in (-36, -26):
    ok = bw.call_method("PlacePrefab", args=(unreal.Name("balustrade_rail_200"), unreal.IntVector(X, y, 5), 0))
    log("rail y=%d -> %s" % (y, ok))

log("after: blocks=%s prefabs=%s" % (bw.call_method("BlockCount"), bw.call_method("PrefabCount")))
ok = bw.call_method("Save")
log("save=%s" % ok)
log("RESULT: " + ("PASS" if ok else "CHECK"))
