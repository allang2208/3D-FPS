"""Register the roman pieces as placeable prefabs in the voxel build palette.

Runs headless:  UnrealEditor-Cmd <uproject> -run=pythonscript -script=<this> -nullrhi -unattended
Footprint is in 20 cm grid cells (the save contract for the building system).
"""

import unreal

PALETTE = "/Game/Building/Voxels/DA_VoxelBuildPalette"
D = "/Game/Props/RomanColumn20260915"
STONE = "/Game/Building/Voxels/M_Voxel_Stone"
WOOD = "/Game/Building/Voxels/M_Voxel_Wood"
MARBLE = D + "/M_WhiteMarble_V2"

ENTRIES = [
    ("roman_column", "罗马柱", D + "/SM_RomanColumn_Detailed", (4, 4, 13), STONE),
    ("balustrade_segment", "围栏整体段", D + "/SM_BalustradeSegment_20", (10, 2, 8), STONE),
    ("voxel_stone", "石块 20", "/Game/Building/Voxels/SM_Voxel20_Stone", (1, 1, 1), STONE),
    ("voxel_wood", "木块 20", "/Game/Building/Voxels/SM_Voxel20_Wood", (1, 1, 1), WOOD),
    ("pavilion_stylobate", "凉亭台基", D + "/SM_PavilionStylobate_20", (32, 32, 1), MARBLE),
    ("pavilion_ring", "凉亭额枋环", D + "/SM_PavilionRing_20", (32, 32, 2), MARBLE),
    ("pavilion_dome", "凉亭穹顶", D + "/SM_PavilionDome_20", (32, 32, 16), MARBLE),
]


def log(m):
    print("[prefab] " + m)


palette = unreal.EditorAssetLibrary.load_asset(PALETTE)
log("palette loaded: %s" % (palette is not None))
log("existing materials: %d" % len(palette.get_editor_property("materials")))

prefabs = []
for pid, name, mesh_path, footprint, surface_path in ENTRIES:
    mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
    surface = unreal.EditorAssetLibrary.load_asset(surface_path)
    if not mesh or not surface:
        log("SKIP %s: mesh=%s surface=%s" % (pid, mesh is not None, surface is not None))
        continue
    entry = unreal.VoxelBuildPrefab()
    entry.set_editor_property("id", pid)
    entry.set_editor_property("display_name", unreal.Text(name))
    entry.set_editor_property("mesh", mesh)
    entry.set_editor_property("footprint", unreal.IntVector(footprint[0], footprint[1], footprint[2]))
    entry.set_editor_property("surface", surface)
    entry.set_editor_property("pivot_offset_cm", unreal.Vector(0.0, 0.0, 0.0))
    prefabs.append(entry)
    log("entry %-20s %-12s %s cells" % (pid, name, "x".join(str(v) for v in footprint)))

palette.set_editor_property("components", prefabs)
saved = unreal.EditorAssetLibrary.save_loaded_asset(palette)
log("saved: %s" % saved)

check = unreal.EditorAssetLibrary.load_asset(PALETTE)
back = check.get_editor_property("components")
log("read back: %d prefabs" % len(back))
for entry in back:
    log("  %-20s %-12s %s" % (entry.get_editor_property("id"),
                              str(entry.get_editor_property("display_name")),
                              entry.get_editor_property("footprint")))
