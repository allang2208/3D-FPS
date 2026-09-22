import unreal as u,json
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
dirty=[p.get_path_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())]
print(json.dumps({'play_world':world.get_path_name() if world else None,'unsaved_packages':dirty,'project':u.Paths.get_project_file_path()}))
