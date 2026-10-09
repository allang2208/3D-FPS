"""Apply existing-function audio routing to the already running editor."""
from pathlib import Path
import unreal as u

O = Path(__file__).parent
log = O.parents[1] / 'Saved/Logs/FPSGAME.log'
offset = log.stat().st_size
u.SystemLibrary.execute_console_command(None, 'LiveCoding.CompileSync')
with log.open('rb') as handle:
    handle.seek(offset)
    current = handle.read().decode('utf-8', errors='replace')
(O / 'livecoding_log_excerpt.txt').write_text(current, encoding='utf-8')
print('SUPER90_AUDIO_COMPILE_RETURNED')
for line in current.splitlines():
    if 'LogLiveCoding' in line or 'Live coding' in line:
        print(line)
