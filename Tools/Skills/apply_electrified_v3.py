"""Save the blade V3 assets in one editor mutex batch. Never start PIE."""
from pathlib import Path
import runpy
import unreal as u

level = u.get_editor_subsystem(u.LevelEditorSubsystem)
if level.is_in_play_in_editor():
    level.editor_request_end_play()
    u.log('ELECTRIFIED_V3_END_PLAY_REQUESTED; rerun after PIE has ended')
else:
    root = Path(u.Paths.project_dir())
    runpy.run_path(str(root / 'Tools/Skills/build_electrified_orbit.py'), run_name='__main__')
    runpy.run_path(str(root / 'Tools/Skills/build_electrified_melee.py'), run_name='__main__')
