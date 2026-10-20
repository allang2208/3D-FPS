import unreal as u,json
es=u.get_editor_subsystem(u.UnrealEditorSubsystem);ls=u.get_editor_subsystem(u.LevelEditorSubsystem)
w=es.get_game_world()
print(json.dumps({'game_world':w.get_path_name() if w else None,'is_pie':ls.is_in_play_in_editor()},ensure_ascii=False),flush=True)
