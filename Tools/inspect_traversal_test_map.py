import unreal,json
from pathlib import Path
s=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);s.load_level('/Game/GameMaps/DayNight_Lighting')
a=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
r=[]
for o in a.get_all_level_actors():
 if isinstance(o,(unreal.PlayerStart,unreal.StaticMeshActor)):
  c,e=o.get_actor_bounds(False)
  r.append(dict(name=o.get_actor_label(),cls=o.get_class().get_name(),pos=str(o.get_actor_location()),rot=str(o.get_actor_rotation()),center=str(c),extent=str(e)))
Path('D:/FPS3D/FPSGAME/Saved/traversal_map_inventory.json').write_text(json.dumps(r,indent=2))
