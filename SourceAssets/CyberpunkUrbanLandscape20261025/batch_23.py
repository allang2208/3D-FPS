import runpy
from pathlib import Path
r=runpy.run_path(str(Path(__file__).resolve().parent/'build_assets.py'))
exec('finish()',r)
print('URBAN_BATCH_DONE',23,flush=True)
