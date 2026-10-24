from pathlib import Path
import runpy
R=Path(__file__).resolve().parent
runpy.run_path(str(R/'build_assets.py'))['main']()
runpy.run_path(str(R/'install_level.py'))['main']()
