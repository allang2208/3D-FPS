"""Background material compilation and import only; no PIE or captures."""
from pathlib import Path
import runpy

root=Path(__file__).parent
runpy.run_path(str(root/'import_distant_ocean.py'),init_globals={'REBUILD_CLOUDS':False})
runpy.run_path(str(root/'refine_cloud_lobes.py'))['apply']()
