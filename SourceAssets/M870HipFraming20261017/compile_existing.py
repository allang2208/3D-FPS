"""Compile the saved placement change in the existing editor without starting gameplay."""
import json
from datetime import datetime
from pathlib import Path
import unreal as u

output = Path(__file__).parent
log = Path(u.Paths.project_log_dir()) / 'FPSGAME.log'
offset = log.stat().st_size if log.exists() else 0
receipt = {'started': datetime.now().isoformat(), 'command': 'LiveCoding.CompileSync',
           'runtime_tested': False, 'base_editor_dll_updated': False, 'status': 'requested'}
(output / 'compile_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
u.log('M870_HIP_COMPILE_BEGIN')
u.SystemLibrary.execute_console_command(editor.get_game_world() or editor.get_editor_world(), 'LiveCoding.CompileSync')
receipt.update(returned=datetime.now().isoformat(), status='command returned; compiler outcome in build log')
(output / 'compile_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
if log.exists():
    with log.open('rb') as stream:
        stream.seek(offset)
        (output / 'editor_compile.log').write_text(stream.read().decode('utf-8', errors='replace'), encoding='utf-8')
print('M870_HIP_COMPILE_RETURNED')
