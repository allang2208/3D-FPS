import runpy
from pathlib import Path
root=Path(__file__).resolve().parent
runpy.run_path(str(root/"author_back_electric_v02.py"),run_name="__main__")
runpy.run_path(str(root.parent/"HitWeakpointV01/import_hit_weakpoint.py"),run_name="__main__")
print("M25_ELECTRIC_AND_HIT_ASSETS_SAVED")
