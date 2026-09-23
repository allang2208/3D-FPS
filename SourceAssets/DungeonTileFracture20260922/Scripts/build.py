"""Reproduce the ceramic pass and optionally install it; no screenshots or tests."""
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
p=argparse.ArgumentParser();p.add_argument('--install',action='store_true');args=p.parse_args()
subprocess.run(['py','-3.11',str(ROOT/'Scripts/author_core.py')],check=True)
blender='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
for script in (ROOT/'Scripts/author_fractures.py',ROOT.parent/'DungeonWorkbenchKit20260921/Scripts/assemble_room_source.py'):
    subprocess.run([blender,'-b','--python-exit-code','1','--python',str(script)],check=True)
if args.install:
    for name in ('import_materials.py','import_and_install.py'):
        receipt=ROOT/'Receipts'/('bridge-'+name+'-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.txt')
        subprocess.run(['powershell','-NoProfile','-File',str(PROJECT/'Tools/AssetPipeline/mcp_call_codex.ps1'),
                        '-PythonScript',str(ROOT/'Scripts'/name),'-OutputFile',str(receipt),'-MaxOutputChars','3000'],check=True)
