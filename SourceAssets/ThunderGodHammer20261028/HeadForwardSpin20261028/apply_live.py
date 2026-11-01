import json
from pathlib import Path
import unreal

root = Path(__file__).resolve().parent
log = Path(unreal.Paths.project_log_dir()) / 'FPSGAME.log'
offset = log.stat().st_size if log.exists() else 0
unreal.SystemLibrary.execute_console_command(None, 'LiveCoding.CompileSync')
tail = ''
if log.exists():
    with log.open('rb') as stream:
        stream.seek(offset)
        tail = stream.read().decode('utf-8', errors='replace')
(root / 'live-compile.log').write_text(tail, encoding='utf-8')
receipt = {
    'mode': 'existing_editor_live_coding',
    'command': 'LiveCoding.CompileSync',
    'log_lines': [line for line in tail.splitlines() if 'Live coding' in line or 'LogLiveCoding:' in line],
    'base_editor_dll_rebuilt': False,
    'gameplay_tested': False,
}
(root / 'live-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(receipt, ensure_ascii=False))
