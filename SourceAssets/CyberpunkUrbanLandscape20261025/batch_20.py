import runpy
from pathlib import Path
r=runpy.run_path(str(Path(__file__).resolve().parent/'build_assets.py'))
exec("assembly('P4')",r)
print('URBAN_BATCH_DONE',20,flush=True)
