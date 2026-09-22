import unreal as u
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world:
    witches=u.GameplayStatics.get_all_actors_of_class(world,u.WitchRebuiltMonster)
    # The current user explicitly approved ending this play session on 2026-09-22.
    print('Ending the current play session with user approval; Witch instances='+str(len(witches)))
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
else:print('PIE already stopped')
