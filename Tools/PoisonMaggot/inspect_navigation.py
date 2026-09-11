import unreal,json
from pathlib import Path
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);level.load_level('/Game/Tests/PoisonMaggot/L_PoisonMaggot');actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);out=[]
for a in actors.get_all_level_actors():
 if isinstance(a,(unreal.NavMeshBoundsVolume,unreal.RecastNavMesh,unreal.PoisonMaggotSpawner)) or a.get_actor_label() in ['Maggot_Floor','Maggot_Obstacle']:
  r={'name':a.get_name(),'class':a.get_class().get_name(),'bounds':str(a.get_actor_bounds(False)),'location':str(a.get_actor_location())}
  for p in ['agent_radius','agent_height','runtime_generation','supported_agents']:
   try:r[p]=str(a.get_editor_property(p))
   except:pass
  out.append(r)
Path('D:/FPS3D/FPSGAME/Saved/PoisonMaggot/nav_inspection.json').write_text(json.dumps(out,indent=2));unreal.log('MAGGOT_NAV_INSPECTED '+json.dumps(out))
