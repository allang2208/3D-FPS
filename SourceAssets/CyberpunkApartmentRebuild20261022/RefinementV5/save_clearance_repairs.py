from pathlib import Path
import runpy
root=Path(__file__).resolve().parent
for name in ['import_meshes.py','install_level.py','inspect_saved.py','read_collision_meshes.py']:
 runpy.run_path(str(root/name),run_name='__main__')
