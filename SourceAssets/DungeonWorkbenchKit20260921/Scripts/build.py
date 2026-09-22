"""One local production entry: authored data -> changed FBX -> serialized UE assemblies."""
from pathlib import Path
from datetime import datetime
import argparse,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
p=argparse.ArgumentParser();p.add_argument('--assets-only',action='store_true');p.add_argument('--materials-only',action='store_true');p.add_argument('--assemble-room-source',action='store_true');args=p.parse_args()
if not args.materials_only:
    subprocess.run([sys.executable,str(ROOT/'Scripts/prepare_bottle_materials.py')],check=True)
    subprocess.run(['E:/Program Files/Blender Foundation/Blender 5.1/blender.exe','-b','--python-exit-code','1','--python',str(ROOT/'Scripts/author_bottles.py')],check=True)
    subprocess.run(['E:/Program Files/Blender Foundation/Blender 5.1/blender.exe','-b','--python-exit-code','1','--python',str(ROOT/'Scripts/author_kit.py')],check=True)
    subprocess.run([sys.executable,str(ROOT/'Scripts/finalize_definition.py')],check=True)
    if args.assemble_room_source:subprocess.run(['E:/Program Files/Blender Foundation/Blender 5.1/blender.exe','-b','--python-exit-code','1','--python',str(ROOT/'Scripts/assemble_room_source.py')],check=True)
if not args.assets_only:
    receipt=ROOT/'Receipts'/('bridge-update-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.txt')
    subprocess.run(['powershell','-NoProfile','-File',str(PROJECT/'Tools/AssetPipeline/mcp_call_codex.ps1'),'-PythonScript',str(ROOT/'Scripts/import_and_install.py'),'-OutputFile',str(receipt),'-MaxOutputChars','3000'],check=True)
