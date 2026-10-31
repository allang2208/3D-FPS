import sys,runpy
from pathlib import Path
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
runpy.run_path(str(R/'build_assets.py'))['main']()
runpy.run_path(str(R/'install_level.py'))['main']()
