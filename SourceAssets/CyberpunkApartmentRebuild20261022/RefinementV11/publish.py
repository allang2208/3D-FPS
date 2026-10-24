from pathlib import Path
import runpy
R=Path(__file__).resolve().parent
for name in ['build_assets.py','compile_materials.py','install_level.py']:runpy.run_path(str(R/name),run_name='__main__')
