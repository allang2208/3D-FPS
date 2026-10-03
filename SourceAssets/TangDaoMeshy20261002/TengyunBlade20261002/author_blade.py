"""Author the current planar, uniform-thickness Tengyun blade revision."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).resolve().parent/'PlanarRepair20261002/author_planar_blade.py'), run_name='__main__')
