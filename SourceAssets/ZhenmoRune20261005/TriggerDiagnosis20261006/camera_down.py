import unreal as u
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
pc=u.GameplayStatics.get_player_controller(w,0)
print('PAUSED_CAMERA_PROPERTY '+str([x for x in dir(pc) if 'paused' in x or 'camera' in x]))
pc.set_editor_property('should_perform_full_tick_when_paused',True)
pc.set_control_rotation(u.Rotator(-75,pc.get_control_rotation().yaw,0))
print('LOOKING_DOWN')
