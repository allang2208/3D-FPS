"""Save the new model, PBR, LOD, weather registration and exclusive icon."""
import runpy
from pathlib import Path
O=Path(__file__).resolve().parent
runpy.run_path(str(O/'import_assets.py'),run_name='__main__')
runpy.run_path(str(O/'import_icon.py'),run_name='__main__')
print('RSH_MUZZLE_BRAKE_IMPORT_COMPLETE',flush=True)
