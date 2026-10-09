import unreal as u,json
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=editor.get_editor_world()
print('POWER_TEXT_EDITOR_STATE '+json.dumps(dict(world=world.get_path_name() if world else None,
 dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
 pie=u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor())))
