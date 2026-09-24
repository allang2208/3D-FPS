"""Necessary live compilation of the existing generator's per-chest collision fields."""
from pathlib import Path
import json
import unreal as u
HERE=Path(__file__).parent
log=HERE.parents[1]/'Saved/Logs/FPSGAME.log'
start=log.stat().st_size if log.exists() else 0
u.SystemLibrary.execute_console_command(None,'LiveCoding.CompileSync')
with log.open('rb') as stream:
    stream.seek(start);lines=stream.read().decode('utf-8',errors='replace').splitlines()
build_lines=[line for line in lines if any(word in line.lower() for word in ('live coding','livecoding','error','result:','patch','compil'))]
(HERE/'native-build.txt').write_text('\n'.join(build_lines),encoding='utf-8')
print('TREASURE_NATIVE_COMPILE_RETURNED '+json.dumps(build_lines[-18:]))
