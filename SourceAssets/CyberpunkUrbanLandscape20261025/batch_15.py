import runpy
from pathlib import Path
r=runpy.run_path(str(Path(__file__).resolve().parent/'build_assets.py'))
exec('meshes(18,21)',r)
print('URBAN_BATCH_DONE',15,flush=True)
