"""Compile existing function bodies without launching or stopping the editor."""
from datetime import datetime
from pathlib import Path
import json
import unreal

project = Path('D:/FPS3D/FPSGAME')
if Path(unreal.Paths.project_dir()).resolve() != project.resolve():
    raise RuntimeError('Unexpected editor project; no compile requested')
output = project / 'SourceAssets/ThunderGodHammer20261028/RecallFixedTime20261031'
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
log = Path(unreal.Paths.project_log_dir()) / 'FPSGAME.log'
offset = log.stat().st_size if log.exists() else 0
started = datetime.now().isoformat()
unreal.log('GUAN_LEI_FIXED_RECALL_COMPILE_BEGIN')
unreal.SystemLibrary.execute_console_command(editor.get_game_world() or editor.get_editor_world(), 'LiveCoding.CompileSync')
unreal.log('GUAN_LEI_FIXED_RECALL_COMPILE_RETURN')
if log.exists():
    with log.open('rb') as stream:
        stream.seek(offset)
        (output / 'live-compile.log').write_text(stream.read().decode('utf-8', errors='replace'), encoding='utf-8')
(output / 'live-compile-request.json').write_text(json.dumps({
    'started': started, 'returned': datetime.now().isoformat(),
    'command': 'LiveCoding.CompileSync', 'gameplay_tested': False,
    'status': 'Compiler output determines success',
}, indent=2), encoding='utf-8')
print('GUAN_LEI_FIXED_RECALL_COMPILE_RETURNED')
