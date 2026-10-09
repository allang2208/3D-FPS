"""Requested window collision diagnosis using the existing editor physics scene."""
from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ed.get_game_world():raise RuntimeError('Preserve the active PIE session')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved editor maps')
previous=ed.get_editor_world().get_path_name().split('.')[0]
script=ROOT/'Scripts/diagnose_window_v6.py'
try:
    exec(compile(script.read_text('utf8'),str(script),'exec'),dict(__file__=str(script),__name__='__main__'))
finally:
    u.EditorLoadingAndSavingUtils.load_map(previous)
print('ECOLOGY_EDITOR_WINDOW_DIAGNOSIS_FINISHED_WITHOUT_SAVING')
