from pathlib import Path
import unreal

out = Path(__file__).resolve().parent / 'native-graph.json'
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(world, f'fps.body.DiagnoseHammerSprint {out.as_posix()}')
if not out.exists():
    raise RuntimeError('Native graph capture did not produce its output.')
print('HAMMER_SPRINT_CAPTURE ' + str(out))
