import unreal as u
s=u.get_editor_subsystem(u.LevelEditorSubsystem)
print('SIMULATING',s.is_in_play_in_editor())
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
print('WORLD',w.get_path_name() if w else None)
print('END',s.editor_request_end_play.__doc__)
if s.is_in_play_in_editor():s.editor_request_end_play()
