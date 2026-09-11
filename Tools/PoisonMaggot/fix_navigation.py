import unreal
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);level.load_level('/Game/Tests/PoisonMaggot/L_PoisonMaggot');actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in actors.get_all_level_actors():
 if isinstance(a,unreal.RecastNavMesh):
  # Commandlets save before asynchronous tile generation finishes. UE 5.8
  # rebuilds newly spawned runtime NavData, but not an empty loaded NavData.
  # Keep the bounds; let the configured agents create fresh data on game load.
  unreal.log('MAGGOT_NAV_RUNTIME_CREATE '+a.get_name());actors.destroy_actor(a)
assert level.save_current_level();unreal.log('MAGGOT_NAV_FIX_COMPLETE')
