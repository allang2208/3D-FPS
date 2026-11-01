import unreal as u
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world:
 u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
 print('M24 asset publication: requested PIE end; editor remains open',flush=True)
else:print('No PIE session is active',flush=True)
