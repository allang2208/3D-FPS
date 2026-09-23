"""Switch the dungeon to already-produced wall assets, without importing again."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('import_and_install.py')), run_name='__main__',
               init_globals={'WALL_SKIP_MESH_IMPORT': True})
