"""One exclusive UE batch: read active takes, save only V2, read compression."""
import runpy
from pathlib import Path
OUT=Path(__file__).resolve().parent
if not (OUT/'before-compressed.json').exists():runpy.run_path(str(OUT/'read_active.py'))
runpy.run_path(str(OUT/'save_all.py'))
runpy.run_path(str(OUT/'read_active.py'),init_globals={'READ_VERSION':'after'})
print('DUAL_REPAIR_ASSETS_AND_COMPRESSED_POSES_COMPLETE',flush=True)
