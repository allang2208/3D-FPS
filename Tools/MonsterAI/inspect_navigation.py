import unreal
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);level.load_level('/Game/Tests/MonsterAI/L_MonsterAI')
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
 if isinstance(a,(unreal.NavMeshBoundsVolume,unreal.RecastNavMesh,unreal.StaticMeshActor)):
  unreal.log('NAV_ACTOR '+a.get_class().get_name()+' '+a.get_actor_label()+' '+str(a.get_actor_bounds(False)))
  for p in ['runtime_generation','agent_radius','agent_height','supported_agents']:
   try:unreal.log('NAV_PROP '+p+' '+str(a.get_editor_property(p)))
   except:pass
