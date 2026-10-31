import runpy
from pathlib import Path
r=runpy.run_path(str(Path(__file__).resolve().parent/'build_assets.py'))
exec('surfaces()',r)
print('URBAN_BATCH_DONE',0,flush=True)
