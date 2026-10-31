import runpy
from pathlib import Path
r=runpy.run_path(str(Path(__file__).resolve().parent/'build_assets.py'))
exec("assembly('P1')",r)
print('URBAN_BATCH_DONE',17,flush=True)
