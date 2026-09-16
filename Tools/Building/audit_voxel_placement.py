"""Headless reproduction of a reported voxel placement failure.

Loads the map, initialises AVoxelBuildWorld without a player controller and places a structure
cell by cell through the real EditCells path, so the same validation the player hits runs.
Rejection reasons are written by the engine (VOXEL_REJECT / VOXEL_AUDIT lines in the log).

Usage (editor closed):
    UnrealEditor-Cmd <uproject> -run=pythonscript -script=Tools/Building/audit_voxel_placement.py -nullrhi -unattended

Defaults reproduce the 2026-09-16 report: a 1-cell-thick wall at x=39 cells, y=-40..-26 cells,
raised from z=0 upwards until a placement is refused.
"""

import unreal

MAP = "/Game/GameMaps/DayNight_Lighting"
WORLD_KEY = "VoxelAudit|DayNight_Lighting"
MATERIAL = "marble"
X_CELL = 39
Y_CELLS = list(range(-40, -25))
TOP_CELL = 16

unreal.EditorLoadingAndSavingUtils.load_map(MAP)
world = unreal.EditorLevelLibrary.get_editor_world()
print("AUDIT map=%s world=%s" % (MAP, world.get_name() if world else None))

# The map's own floor is not reliably traceable in a headless commandlet, so the audit builds on a
# slab it spawns itself: 100 m x 100 m x 1 m cube with BlockAll, top surface at z = 0.
floor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(780.0, -660.0, -50.0))
cube = unreal.load_asset("/Engine/BasicShapes/Cube.Cube")
if floor and cube:
    component = floor.static_mesh_component
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    component.set_static_mesh(cube)
    component.set_collision_profile_name("BlockAll")
    floor.set_actor_scale3d(unreal.Vector(100.0, 100.0, 1.0))
    print("AUDIT floor slab spawned: top z=0, 100x100 m")
else:
    print("AUDIT floor slab failed (actor=%s mesh=%s)" % (floor is not None, cube is not None))

build = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.VoxelBuildWorld, unreal.Vector(0.0, 0.0, 0.0))
print("AUDIT spawned=%s initialize=%s" % (build is not None, build.debug_initialize(WORLD_KEY) if build else None))
if not build:
    raise SystemExit(1)

stopped_at = None
for z in range(TOP_CELL):
    placed = 0
    for y in Y_CELLS:
        cell = [unreal.IntVector(X_CELL, y, z)]
        if build.edit_cells(cell, unreal.Name(MATERIAL)):
            placed += 1
        elif stopped_at is None:
            stopped_at = (z, y)
    print("AUDIT layer z=%2d (%4.2f m up): placed %d/%d%s" % (
        z, z * 0.2, placed, len(Y_CELLS), "" if placed == len(Y_CELLS) else "   <-- INCOMPLETE"))
    if placed == 0:
        print("AUDIT stopped at z=%d (%.2f m)" % (z, z * 0.2))
        break

print("AUDIT done, first refusal=%s" % (stopped_at,))
