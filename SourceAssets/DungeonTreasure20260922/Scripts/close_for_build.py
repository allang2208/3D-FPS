import unreal as u
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue.get_game_world():raise RuntimeError('Play must finish before regular native build')
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
if dirty:raise RuntimeError('Preserve unsaved editor packages: '+', '.join(p.get_name() for p in dirty[:8]))
u.SystemLibrary.quit_editor()
print('TREASURE_EDITOR_NORMAL_EXIT_REQUESTED')
