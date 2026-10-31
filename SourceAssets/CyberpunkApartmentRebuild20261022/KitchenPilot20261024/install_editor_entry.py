"""Single guarded entry point for the scoped apartment map write batch.
Never stop the current PIE: its owner may have started a different game run.
"""
from pathlib import Path
import runpy
import unreal as u
root = Path(__file__).resolve().parent
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
level = u.get_editor_subsystem(u.LevelEditorSubsystem)
if level.is_in_play_in_editor() or (editor and editor.get_game_world()):
    raise RuntimeError('Preserve current PIE; map write deferred without stopping play, loading or saving a map')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
    raise RuntimeError('Preserve unsaved maps; stop-PIE did not authorize saving unrelated work')
runpy.run_path(str(root / 'install_level.py'), run_name='__main__')
