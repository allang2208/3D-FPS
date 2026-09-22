"""Regenerate the deterministic stock arrangement, then import through the shared bridge."""
from pathlib import Path
from datetime import datetime
import subprocess,argparse
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
p=argparse.ArgumentParser();p.add_argument('--assets-only',action='store_true');args=p.parse_args()
blender='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
for script in [ROOT/'Scripts/author_rack.py',ROOT.parent/'DungeonWorkbenchKit20260921/Scripts/assemble_room_source.py']:
    subprocess.run([blender,'-b','--python-exit-code','1','--python',str(script)],check=True)
if not args.assets_only:
    receipt=ROOT/'Receipts'/('bridge-install-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.txt')
    subprocess.run(['powershell','-NoProfile','-File',str(PROJECT/'Tools/AssetPipeline/mcp_call_codex.ps1'),'-PythonScript',str(ROOT/'Scripts/import_and_install.py'),'-OutputFile',str(receipt),'-MaxOutputChars','3000'],check=True)
