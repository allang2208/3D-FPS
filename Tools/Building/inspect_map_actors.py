"""List actors and bounds in a map, optionally filtered to a world-space box.

Used to find scene geometry that blocks voxel placement (ScenePlacementAllowed traces the scene
around each planned cell). Run headless:
    UnrealEditor-Cmd <uproject> -run=pythonscript -script=Tools/Building/inspect_map_actors.py -nullrhi -unattended
"""

import unreal

MAP = "/Game/GameMaps/DayNight_Lighting"
# Voxel wall from the 2026-09-16 save: x=39 cells, y=-40..-26 cells, z 0..9 cells (20 cm cells).
FILTER_MIN = unreal.Vector(39 * 20 - 200, -40 * 20 - 200, -40)
FILTER_MAX = unreal.Vector(39 * 20 + 400, -26 * 20 + 200, 600)

unreal.EditorLoadingAndSavingUtils.load_map(MAP)
world = unreal.EditorLevelLibrary.get_editor_world()
print("map %s world=%s" % (MAP, world is not None))

rows = []
for actor in unreal.EditorLevelLibrary.get_all_level_actors():
    if not actor:
        continue
    origin, extent = actor.get_actor_bounds(False)
    center = origin
    if (center.x + extent.x < FILTER_MIN.x or center.x - extent.x > FILTER_MAX.x or
            center.y + extent.y < FILTER_MIN.y or center.y - extent.y > FILTER_MAX.y or
            center.z + extent.z < FILTER_MIN.z or center.z - extent.z > FILTER_MAX.z):
        continue
    label = actor.get_actor_label()
    cls = actor.get_class().get_name()
    blocks = ""
    for component in actor.get_components_by_class(unreal.PrimitiveComponent):
        if component.is_collision_enabled() and component.get_collision_profile_name() not in ("NoCollision",):
            blocks = component.get_collision_profile_name()
            break
    rows.append((label, cls, center, extent, blocks))

print("actors overlapping the wall column region: %d" % len(rows))
for label, cls, center, extent, blocks in sorted(rows, key=lambda r: r[2].z):
    print("  %-28s %-24s center=(%8.1f,%8.1f,%8.1f) extent=(%7.1f,%7.1f,%7.1f) z=%.1f..%.1f collision=%s" % (
        label, cls, center.x, center.y, center.z, extent.x, extent.y, extent.z,
        center.z - extent.z, center.z + extent.z, blocks or "none"))
