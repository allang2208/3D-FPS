import runpy
from pathlib import Path
r=runpy.run_path(str(Path(__file__).resolve().parent/'build_assets.py'))
exec("foliage('Flower')",r)
print('URBAN_BATCH_DONE',7,flush=True)
