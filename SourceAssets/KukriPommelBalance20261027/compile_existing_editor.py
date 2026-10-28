"""Compile the saved implementation changes in the existing editor, without PIE."""
import json
from datetime import datetime
from pathlib import Path
import unreal

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/KukriPommelBalance20261027'
if Path(unreal.Paths.project_dir()).resolve() != ROOT.resolve():
    raise RuntimeError('Unexpected editor project')
log = Path(unreal.Paths.project_log_dir()) / 'FPSGAME.log'
offset = log.stat().st_size if log.exists() else 0
receipt = {'started': datetime.now().isoformat(), 'command': 'LiveCoding.CompileSync',
           'runtime_tested': False, 'result': 'pending'}
(OUT / 'compile_request.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
unreal.log('KUKRI_POMMEL_COMPILE_BEGIN')
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = editor.get_game_world() or editor.get_editor_world()
unreal.SystemLibrary.execute_console_command(world, 'LiveCoding.CompileSync')
receipt.update(returned=datetime.now().isoformat(), result='command returned; see compiler output')
(OUT / 'compile_request.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
if log.exists():
    with log.open('rb') as stream:
        stream.seek(offset)
        text = stream.read().decode('utf-8', errors='replace')
    (OUT / 'editor_compile.log').write_text(text, encoding='utf-8')
unreal.log('KUKRI_POMMEL_COMPILE_RETURNED')
