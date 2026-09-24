"""Finish this asset edit after ending the PIE session; never start a game or editor."""
from pathlib import Path
import unreal as u
HERE=Path(__file__).parent
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
if editor.get_game_world():
    level.editor_request_end_play()
    print('TREASURE_REPAIR_END_PLAY_REQUESTED')
else:
    import runpy
    runpy.run_path(str(HERE/'install_finished_chest.py'),run_name='__main__')
