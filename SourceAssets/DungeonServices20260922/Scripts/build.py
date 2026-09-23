"""Produce editable sources and FBX/PBR deliverables; no runtime launch."""
import runpy,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT/'Scripts/author_surfaces.py'),run_name='__main__')
subprocess.run(['E:/Program Files/Blender Foundation/Blender 5.1/blender.exe','-b','--python-exit-code','1','--python',str(ROOT/'Scripts/author_services.py')],check=True)
