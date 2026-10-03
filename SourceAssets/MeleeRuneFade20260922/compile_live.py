"""Compile existing function edits synchronously, preserving open unsaved assets."""
import json
from pathlib import Path
from datetime import datetime
import unreal as u

P = Path(__file__).resolve().parent
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world() is not None:
    raise RuntimeError('Active play preserved; compile after play ends.')
request = {'started': datetime.now().isoformat(), 'command': 'LiveCoding.CompileSync',
           'result': 'Pending compiler output', 'tested': False}
(P / 'compile-request.json').write_text(json.dumps(request, indent=2), encoding='utf-8')
u.log('MELEE_RUNE_FADE_COMPILE_BEGIN ' + request['started'])
u.SystemLibrary.execute_console_command(editor.get_editor_world(), 'LiveCoding.CompileSync')
request['returned'] = datetime.now().isoformat()
request['result'] = 'Command returned; use this compilation output for the actual result'
(P / 'compile-request.json').write_text(json.dumps(request, indent=2), encoding='utf-8')
u.log('MELEE_RUNE_FADE_COMPILE_RETURN ' + request['returned'])
