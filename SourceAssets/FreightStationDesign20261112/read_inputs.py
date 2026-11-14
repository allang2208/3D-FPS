"""Entry point of the queued design batch: capture, derive contacts, then install."""
from pathlib import Path
import json, os, runpy, subprocess

root=Path(__file__).resolve().parent
receipt=root/'install-receipt.json'
if not receipt.exists() or json.loads(receipt.read_text('utf8')).get('stage')!='map_saved':
    runpy.run_path(str(root/'capture_scene.py'),run_name='__main__')
    # The standalone author uses the project workstation's NumPy. UE retains its
    # existing shared batch slot until the contacts have been installed and saved.
    python=Path(os.environ['LOCALAPPDATA'])/'Programs/Python/Python311/python.exe'
    result=subprocess.run([str(python),'-E',str(root/'author_points.py')],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode: raise RuntimeError(result.stderr[-3000:])
    print(result.stdout,flush=True)
    runpy.run_path(str(root/'install.py'),run_name='__main__')
