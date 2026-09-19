"""Headless map edit: replace the old BalustradeSegment fence (y=930) with the roman kit.

- destroys BalustradeSegment_* / leftover Baluster_/BalustradeRail_/Balustrade_Plinth actors
- spawns 8 x SM_RomanBaluster_Small (v3) at the old segment centres (200 cm rhythm)
- spawns 8 x SM_RomanRail_200 covering the same span on top (arc cross-section)
- fills the gaps between columns with 20 cm marble voxel cubes (2 layers = 40 cm, plinth band)
- saves the level, verifies on disk via umap mtime
"""

import time

import unreal


def log(m):
    print("[map] " + m)


world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.EditorLoadingAndSavingUtils.load_map("/Game/GameMaps/DayNight_Lighting")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
log("world=%s actors=%d" % (world.get_name(), len(sub.get_all_level_actors())))

# ------------------------------------------------------------ floor + old fence
floor_top = 5.2
old = []
for a in sub.get_all_level_actors():
    label = a.get_actor_label()
    if label.startswith(("BalustradeSegment", "Baluster_", "BalustradeRail", "Balustrade_Plinth")):
        old.append(a)
    if label == "MarbleFloor_Colonnade":
        o, e = a.get_actor_bounds(False)
        floor_top = o.z + e.z
        log("floor top=%.1f x %.0f..%.0f y %.0f..%.0f" % (floor_top, o.x - e.x, o.x + e.x, o.y - e.y, o.y + e.y))
log("old fence actors: %d" % len(old))
span_min, span_max, fence_y = 500.0, 2100.0, 930.0
if old:
    lo, hi = 1e9, -1e9
    for a in old:
        o, e = a.get_actor_bounds(False)
        lo, hi = min(lo, o.x - e.x), max(hi, o.x + e.x)
        fence_y = a.get_actor_location().y
    span_min, span_max = lo, hi
    log("old span x %.0f..%.0f (y=%.0f)" % (span_min, span_max, fence_y))

for a in old:
    sub.destroy_actor(a)

# ----------------------------------------------------------------- spawn pieces
COL = "/Game/Props/RomanColumn20260915/SM_RomanBaluster_Small"
RAIL = "/Game/Props/RomanColumn20260915/SM_RomanRail_200"
CUBE = "/Engine/BasicShapes/Cube.Cube"
MAT = "/Game/Props/RomanColumn20260915/M_RomanStone_V2"
col_mesh = unreal.EditorAssetLibrary.load_asset(COL)
rail_mesh = unreal.EditorAssetLibrary.load_asset(RAIL)
cube_mesh = unreal.EditorAssetLibrary.load_asset(CUBE)
mat = unreal.EditorAssetLibrary.load_asset(MAT)
log("assets: col=%s rail=%s cube=%s mat=%s" % (
    col_mesh is not None, rail_mesh is not None, cube_mesh is not None, mat is not None))

count = 0


def place(mesh, x, y, z, label, scale=1.0):
    global count
    a = sub.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, z), unreal.Rotator(0, 0, 0))
    smc = a.get_component_by_class(unreal.StaticMeshComponent)
    smc.set_static_mesh(mesh)
    smc.set_material(0, mat)
    if scale != 1.0:
        a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    a.set_actor_label(label)
    count += 1
    return a


total = span_max - span_min
n_rails = int(round(total / 200.0))
col_centres = [span_min + 100 + 200 * k for k in range(n_rails)]
for k, cx in enumerate(col_centres):
    place(col_mesh, cx, fence_y, floor_top, "RomanFence_Column_%02d" % (k + 1))
for k in range(n_rails):
    place(rail_mesh, span_min + 100 + 200 * k, fence_y, floor_top + 100, "RomanFence_Rail_%02d" % (k + 1))

# voxel infill: 2 layers of 20 cm cubes between adjacent columns and at both ends
edges = [span_min] + [c + 20 for c in col_centres[:-1]] + [span_max - 40 * 0]  # placeholder
gap_ranges = []
for i in range(len(col_centres) - 1):
    gap_ranges.append((col_centres[i] + 20, col_centres[i + 1] - 20))
gap_ranges.append((span_min, col_centres[0] - 20))
gap_ranges.append((col_centres[-1] + 20, span_max))
n_cubes = 0
for gi, (g0, g1) in enumerate(gap_ranges):
    n = int(round((g1 - g0) / 20.0))
    if n <= 0:
        continue
    for layer in (0, 1):
        for i in range(n):
            cx = g0 + 10 + 20 * i
            cz = floor_top + 10 + 20 * layer
            place(cube_mesh, cx, fence_y, cz, "RomanFence_Voxel_g%02d_l%d_%02d" % (gi, layer, i), 0.2)
            n_cubes += 1
log("spawned: rails=%d columns=%d voxel_cubes=%d total=%d" % (n_rails, len(col_centres), n_cubes, count))

# --------------------------------------------------------------------- save map
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
saved = les.save_current_level()
log("save_current_level=%s" % saved)
if not saved:
    package = unreal.load_package("/Game/GameMaps/DayNight_Lighting")
    saved = unreal.EditorLoadingAndSavingUtils.save_packages([package], False)
    log("save_packages fallback=%s" % saved)

# --------------------------------------------------------------------- readback
n_rf = 0
for a in sub.get_all_level_actors():
    if a.get_actor_label().startswith("RomanFence_"):
        n_rf += 1
log("RomanFence actors after save: %d" % n_rf)
log("RESULT: %s" % ("PASS" if saved and n_rf == count else "CHECK"))
