import json,unreal as u
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
w=ue.get_editor_world();g=ue.get_game_world()
print(json.dumps(dict(editor=w.get_path_name() if w else None,game=g.get_path_name() if g else None,
    dirty=[p.get_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())])))
