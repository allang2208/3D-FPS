"""Record the failing saved material, then rebuild its visible wet surface."""
import runpy
from pathlib import Path

folder = Path(__file__).resolve().parent
runpy.run_path(str(folder/'inspect_pus_visibility.py'), run_name='__main__')
runpy.run_path(str(folder/'build_pus_material.py'), run_name='__main__')
