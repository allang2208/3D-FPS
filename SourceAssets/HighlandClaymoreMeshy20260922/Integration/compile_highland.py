"""Compile necessary existing-function edits; does not enter PIE."""
from datetime import datetime
from pathlib import Path
import json
import unreal as u
P=Path(__file__).resolve().parent
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world() is not None:raise RuntimeError('Finish PIE before the integration build.')
start=datetime.now().isoformat();u.log('HIGHLAND_INTEGRATION_COMPILE_BEGIN '+start)
u.SystemLibrary.execute_console_command(editor.get_editor_world(),'LiveCoding')
u.SystemLibrary.execute_console_command(editor.get_editor_world(),'LiveCoding.CompileSync')
(P/'compile-request.json').write_text(json.dumps({'started':start,'returned':datetime.now().isoformat(),'command':'LiveCoding.CompileSync','scope':'warehouse grant, sword preview lighting, native rune material routing','tested':False},indent=2),encoding='utf-8')
u.log('HIGHLAND_INTEGRATION_COMPILE_RETURN')
