"""Headless: two-layer (40 cm) infill matching the baluster plinth band.

Relayout: remove the single 20 cm layer, lay two layers (z 20..60 world, 40 cm tall total)
so the infill band tops out level with the column plinth (plinth = 0..40 cm of the column).
"""

import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.EditorLoadingAndSavingUtils.load_map("/Game/GameMaps/DayNight_Lighting")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
print("[flat40] world=%s" % world.get_name())

floor_top = 20.0
for a in sub.get_all_level_actors():
    if a.get_actor_label() == "MarbleFloor_Colonnade":
        o, e = a.get_actor_bounds(False)
        floor_top = o.z + e.z
print("[flat40] floor_top=%.1f" % floor_top)

removed = 0
centres = []
for a in list(sub.get_all_level_actors()):
    label = a.get_actor_label()
    if label.startswith("RomanFence_Voxel_"):
        sub.destroy_actor(a)
        removed += 1
    elif label.startswith("RomanFence_Column_"):
        centres.append(a.get_actor_location().x)
centres.sort()
print("[flat40] removed=%d columns=%d" % (removed, len(centres)))

cube = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube.Cube")
mat = unreal.EditorAssetLibrary.load_asset("/Game/Props/RomanColumn20260915/M_RomanStone_V2")
span_min, span_max = min(centres) - 100, max(centres) + 100
gap_ranges = [(span_min, centres[0] - 20)]
for i in range(len(centres) - 1):
    gap_ranges.append((centres[i] + 20, centres[i + 1] - 20))
gap_ranges.append((centres[-1] + 20, span_max))

n = 0
for gi, (g0, g1) in enumerate(gap_ranges):
    count = int(round((g1 - g0) / 20.0))
    for layer in (0, 1):
        for i in range(count):
            a = sub.spawn_actor_from_class(unreal.StaticMeshActor,
                                           unreal.Vector(g0 + 10 + 20 * i, 930.0, floor_top + 10 + 20 * layer),
                                           unreal.Rotator(0, 0, 0))
            smc = a.get_component_by_class(unreal.StaticMeshComponent)
            smc.set_static_mesh(cube)
            smc.set_material(0, mat)
            a.set_actor_scale3d(unreal.Vector(0.2, 0.2, 0.2))
            a.set_actor_label("RomanFence_Voxel_40_g%02d_l%d_%02d" % (gi, layer, i))
            n += 1
print("[flat40] 40cm infill cubes placed: %d" % n)

saved = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
print("[flat40] save=%s" % saved)
back = sum(1 for a in sub.get_all_level_actors() if a.get_actor_label().startswith("RomanFence_Voxel_40"))
print("[flat40] RESULT: %s (40cm cubes=%d)" % ("PASS" if saved and back == n else "CHECK", back))
