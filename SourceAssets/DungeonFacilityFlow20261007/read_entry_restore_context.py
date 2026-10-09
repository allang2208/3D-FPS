"""Read only the live map/services needed to restore the authored entrance."""
import unreal as u, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=u.load_asset('/Game/GameMaps/L_Dungeon_Randomized')
rows=[]
for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    label=a.get_actor_label()
    if label.startswith(('DGN_A_','DGN_Start_','FacilityFlow_')) or isinstance(a,u.PlayerStart):
        rows.append(dict(label=label,position=list(a.get_actor_location().to_tuple()),
            rotation=list(a.get_actor_rotation().to_tuple()),scale=list(a.get_actor_scale3d().to_tuple()),
            hidden=a.get_editor_property('hidden'),components=[dict(name=c.get_name(),
            mesh=c.static_mesh.get_path_name() if c.static_mesh else None,
            transform=str(c.get_relative_transform()),collision=str(c.get_collision_profile_name()))
            for c in a.get_components_by_class(u.StaticMeshComponent)]))
g=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator))
(ROOT/'Sources/entry-restore-live-catalog.json').write_text(g.get_editor_property('module_catalog_json'),encoding='utf8')
report=dict(current_map=ed.get_editor_world().get_path_name(),playing=bool(ed.get_game_world()),
    dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],actors=rows)
(ROOT/'Sources/entry-restore-live-context.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('ENTRY_RESTORE_CONTEXT',report['current_map'],'PIE',report['playing'],'dirty',report['dirty'],'actors',len(rows))
