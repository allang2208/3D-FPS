"""Author the wall revision; --install also imports and saves it in UE. No tests."""
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
p = argparse.ArgumentParser()
p.add_argument('--install', action='store_true')
args = p.parse_args()
subprocess.run(['py', '-3.11', str(ROOT/'Scripts/author_surfaces.py')], check=True)
subprocess.run(['E:/Program Files/Blender Foundation/Blender 5.1/blender.exe', '-b', '--python-exit-code', '1',
                '--python', str(ROOT/'Scripts/author_walls.py')], check=True)
if args.install:
    for script in ('import_materials.py', 'import_and_install.py'):
        receipt = ROOT/'Receipts'/('bridge-'+script+'-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.txt')
        subprocess.run(['powershell', '-NoProfile', '-File', str(PROJECT/'Tools/AssetPipeline/mcp_call_codex.ps1'),
                        '-PythonScript', str(ROOT/'Scripts'/script), '-OutputFile', str(receipt),
                        '-MaxOutputChars', '3000'], check=True)
