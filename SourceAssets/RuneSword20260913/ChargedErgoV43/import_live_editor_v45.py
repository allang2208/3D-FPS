"""Import the V45 revision into the owning editor over the Python remote socket."""
import runpy
from pathlib import Path
import unreal as u

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('End the active PIE session before importing charged attack animations.')
flag = 'Interchange.FeatureFlags.Import.FBX'
prior = u.SystemLibrary.get_console_variable_int_value(flag)
try:
    runpy.run_path(str(Path(__file__).with_name('import_revision_v45.py')), run_name='__main__')
finally:
    u.SystemLibrary.execute_console_command(None, f'{flag} {prior}')
