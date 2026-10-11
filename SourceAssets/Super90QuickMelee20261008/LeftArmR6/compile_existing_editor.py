"""Compile a function-body-only node change into the existing editor."""
from datetime import datetime
from pathlib import Path
import json
import unreal as u

O = Path(__file__).parent
if Path(u.Paths.project_dir()).resolve() != O.parents[2].resolve():
    raise RuntimeError('Unexpected editor project')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
started = datetime.now().isoformat()
u.log('SUPER90_MELEE_R6_COMPILE_BEGIN '+started)
u.SystemLibrary.execute_console_command(editor.get_editor_world(), 'LiveCoding.CompileSync')
(O/'compile_request.json').write_text(json.dumps(dict(
    started=started, returned=datetime.now().isoformat(), command='LiveCoding.CompileSync',
    source='Source/FPSGAME/Weapons/Super90SupportArmNode.cpp',
    status='Compiler log determines success; request alone is not completion', runtime_tested=False), indent=2))
u.log('SUPER90_MELEE_R6_COMPILE_RETURNED')
