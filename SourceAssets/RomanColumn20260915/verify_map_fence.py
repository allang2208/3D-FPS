import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.EditorLoadingAndSavingUtils.load_map("/Game/GameMaps/DayNight_Lighting")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
cols = rails = cubes = old = 0
for a in sub.get_all_level_actors():
    label = a.get_actor_label()
    if label.startswith("RomanFence_Column_"): cols += 1
    elif label.startswith("RomanFence_Rail_"): rails += 1
    elif label.startswith("RomanFence_Voxel_"): cubes += 1
    elif label.startswith(("BalustradeSegment", "Baluster_", "BalustradeRail")): old += 1
print("[verify] fresh-load: columns=%d rails=%d voxel_cubes=%d old_fence_left=%d" % (cols, rails, cubes, old))
for a in sub.get_all_level_actors():
    if a.get_actor_label() == "RomanFence_Column_01":
        o, e = a.get_actor_bounds(False)
        print("[verify] column_01 bbox x %.0f..%.0f z %.1f..%.1f" % (o.x-e.x, o.x+e.x, o.z-e.z, o.z+e.z))
    if a.get_actor_label() == "RomanFence_Rail_08":
        o, e = a.get_actor_bounds(False)
        print("[verify] rail_08 bbox x %.0f..%.0f z %.1f..%.1f" % (o.x-e.x, o.x+e.x, o.z-e.z, o.z+e.z))
