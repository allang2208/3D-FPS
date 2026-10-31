from pathlib import Path
import runpy
R=Path(__file__).resolve().parent
runpy.run_path(str(R/'materials.py'))['main']()
runpy.run_path(str(R/'import_meshes.py'))['main']()
runpy.run_path(str(R/'install_level.py'))['main'](background=True)
