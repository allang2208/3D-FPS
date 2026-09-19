import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.EditorLoadingAndSavingUtils.load_map("/Game/GameMaps/DayNight_Lighting")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
print("[tr] world=%s" % world.get_name())
for label, x, y in (("origin", 0.0, 0.0), ("column site", 600.0, 600.0), ("build site", 570.0, -670.0)):
    hit = unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(x, y, 50.0), unreal.Vector(x, y, -50.0),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)
    if not hit:
        print("[tr] %-11s NO HIT" % label)
    else:
        print("[tr] %-11s comp=%s z=%.1f" % (label, hit.component.get_name() if hit.component else "-", hit.location.z))
