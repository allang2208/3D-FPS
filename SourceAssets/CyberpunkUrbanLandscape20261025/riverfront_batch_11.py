from pathlib import Path
import runpy
R=Path(__file__).resolve().parent
r=runpy.run_path(str(R/'build_assets.py'))
r['finish']()
print('RIVERFRONT_BATCH_SAVED',11,flush=True)
