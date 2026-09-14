"""Read the failing map's saved navigation setup without modifying it."""
import unreal as u, json
from pathlib import Path

level=u.get_editor_subsystem(u.LevelEditorSubsystem)
if not level.load_level('/Game/GameMaps/DayNight_Lighting'):
    raise RuntimeError('Cannot load the map reported by the gameplay log')
actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
records=[]
for actor in actors:
    if isinstance(actor,(u.NavMeshBoundsVolume,u.RecastNavMesh,u.StaticMeshActor,u.PlayerStart)):
        origin,extent=actor.get_actor_bounds(False)
        record={'name':actor.get_actor_label(),'class':actor.get_class().get_name(),
                'origin':[origin.x,origin.y,origin.z],'extent':[extent.x,extent.y,extent.z]}
        if isinstance(actor,u.RecastNavMesh):
            for key in ('agent_radius','agent_height','runtime_generation'):
                record[key]=str(actor.get_editor_property(key))
        if isinstance(actor,u.StaticMeshActor):
            component=actor.static_mesh_component
            record['mesh']=component.static_mesh.get_path_name() if component.static_mesh else None
            record['collision_profile']=str(component.get_collision_profile_name())
        records.append(record)
out=Path('D:/FPS3D/FPSGAME/Saved/FatZombieNavigation')
out.mkdir(parents=True,exist_ok=True)
(out/'saved_map_before.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
u.log('FAT_NAV_SAVED_MAP '+json.dumps(records))
