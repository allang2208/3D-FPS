"""Author clean mixed-source versions from the recoverable trash originals."""
from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
plan=json.loads((ROOT/'Config/retirement.json').read_text())
for entry in plan['entries']:
    if entry['phase']!='mixed_sources' or not entry['relative'].endswith('.blend'):continue
    subprocess.run(['E:/Program Files/Blender Foundation/Blender 5.1/blender.exe','-b','--python-exit-code','1','--python',str(ROOT/'Scripts/prune_source_scene.py'),'--',entry['relative']],check=True)
