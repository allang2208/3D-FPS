import unreal as u
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE restarted; preserve editor')
if u.EditorLoadingAndSavingUtils.get_dirty_content_packages() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
    raise RuntimeError('Unsaved assets appeared; preserve editor')
print('SUPER90_NORMAL_EDITOR_EXIT_FOR_BASE_DLL_BUILD')
u.SystemLibrary.quit_editor()
