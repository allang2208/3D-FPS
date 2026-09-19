"""Start ComfyUI from WMI, so closing SSH does not end the service."""
import json
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1])
stage = Path('D:/Mechanical3DSetup')
with (stage / 'comfy-activation.stdout.log').open('ab') as out, \
     (stage / 'comfy-activation.stderr.log').open('ab') as err:
    child = subprocess.Popen(
        [str(root / '.venv/Scripts/python.exe'), 'main.py', '--listen', '0.0.0.0',
         '--port', '8188', '--enable-cors-header', '*', '--disable-xformers'],
        cwd=root, stdout=out, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW)
(stage / 'activation.json').write_text(json.dumps({
    'started_pid': child.pid, 'purpose': 'activate installed nodes', 'tests_run': False
}, indent=2), encoding='utf-8')
