"""Read package ownership before the authorized background save/retirement."""
import json
import unreal as u
targets=['/Game/GameMaps/Design/L_AbandonedIncineratorHall_Subject','/Game/GameMaps/L_Dungeon_Randomized','/Game/GameMaps/Design/L_AbandonedDataArchive_Subject']
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
game=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
result=dict(editor_world=w.get_path_name() if w else None,
    game_world=game.get_path_name() if game else None,
    generators=[a.get_path_name() for a in actors if isinstance(a,u.AuthoredDungeonGenerator)],
    loaded={p:bool(u.find_object(None,p+'.'+p.rsplit('/',1)[-1])) for p in targets},
    dirty=[p.get_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())])
print('TARGET_PACKAGE_OWNERSHIP '+json.dumps(result,ensure_ascii=False))
