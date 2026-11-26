"""Rebuild the village using the current demo-derived wall authoring recipe."""
from pathlib import Path
import runpy
folder=Path(__file__).resolve().parent
runpy.run_path(str(folder/'extract_wall_patterns.py'),run_name='__main__')
runpy.run_path(str(folder/'restyle_walls.py'),run_name='__main__')
