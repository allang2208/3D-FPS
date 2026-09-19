"""Import only this revision into the owning editor when Windows holds its files."""
import runpy
from pathlib import Path
import unreal as u

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('End the active PIE session before importing guard animations.')
flag='Interchange.FeatureFlags.Import.FBX'
prior=u.SystemLibrary.get_console_variable_int_value(flag)
try:
    runpy.run_path(str(Path(__file__).with_name('import_revision.py')),run_name='__main__')
finally:
    u.SystemLibrary.execute_console_command(None,f'{flag} {prior}')
