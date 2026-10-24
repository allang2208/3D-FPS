from pathlib import Path
import runpy
root=Path(__file__).resolve().parent
runpy.run_path(str(root/'build_surfaces.py'),run_name='__main__')
runpy.run_path(str(root/'import_meshes.py'),run_name='__main__')
runpy.run_path(str(root/'install_level.py'),run_name='__main__')
