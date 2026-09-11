import unreal,json
from pathlib import Path
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report=[]
for name,center,extent in [('/Game/GameMaps/L_Normandy_FPS_Test',unreal.Vector(-2801,34024,-11381),unreal.Vector(6500,6500,2000)),('/Game/Tests/MonsterAI/L_MonsterAI',unreal.Vector(0,0,250),unreal.Vector(1800,1500,600))]:
 assert level.load_level(name)
 world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
 assert unreal.MonsterAIController.build_navigation_bounds(world,center,extent)
 volume=next(a for a in actors.get_all_level_actors() if isinstance(a,unreal.NavMeshBoundsVolume) and a.get_actor_label()=='MonsterNavigation')
 origin,size=volume.get_actor_bounds(False);assert size.x>100 and size.y>100,str(size)
 assert level.save_current_level();report.append({'map':name,'bounds':str(size)})
Path('D:/FPS3D/FPSGAME/Saved/MonsterAI/navigation.json').write_text(json.dumps(report,indent=2));unreal.log('MONSTER_NAV_BOUNDS_VERIFIED')
