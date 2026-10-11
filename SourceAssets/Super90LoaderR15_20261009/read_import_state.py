import unreal as u,json
s=u.get_editor_subsystem(u.LevelEditorSubsystem)
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
e=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
print(json.dumps(dict(game_world=w.get_path_name() if w else None,editor_world=e.get_path_name() if e else None,
    play_methods=[n for n in dir(s) if 'play' in n.lower()],
    dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]+[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])),flush=True)
