"""Normal close only when there is no play session and no unsaved work."""
import unreal as u
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():raise RuntimeError('Preserve running play; native build pending')
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
if dirty:raise RuntimeError('Preserve unsaved packages; native build pending: '+', '.join(p.get_name() for p in dirty[:8]))
print('Dungeon boss integration: normal editor close for the new encounter class')
u.SystemLibrary.execute_console_command(editor.get_editor_world(),'QUIT_EDITOR')
