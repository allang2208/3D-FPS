import unreal as u
print('UNSAVED_PACKAGES', len(u.EditorLoadingAndSavingUtils.get_dirty_content_packages()) + len(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()))
print('QUIT_API', hasattr(u.SystemLibrary, 'quit_editor'))
