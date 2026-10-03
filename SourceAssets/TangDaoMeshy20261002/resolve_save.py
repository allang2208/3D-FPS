import unreal as u
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
print('TANGDAO_SAVE_CONTEXT', u.SystemLibrary.get_command_line(), 'PLAY_WORLD', editor.get_game_world() if editor else None)
texture = u.load_asset('/Game/Weapons/TangDao20261002/Textures/T_TangDao_BaseColor')
if texture:
    print('TANGDAO_TEXTURE_PACKAGE', texture.get_outermost().get_path_name())
    print('TANGDAO_PACKAGE_SAVE', u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()], False))
