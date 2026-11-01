import unreal as u
sub = u.get_editor_subsystem(u.LevelEditorSubsystem)
print('M24_EDITOR_SAVE_CONTEXT', {'pie': sub.is_in_play_in_editor(), 'project': u.Paths.project_dir()}, flush=True)
