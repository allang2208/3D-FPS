import unreal as u
p=u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()
print('PIE=',p,'DIRTY_TARGETS=',[x.get_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if '/Weapons/M24/' in x.get_name()])
