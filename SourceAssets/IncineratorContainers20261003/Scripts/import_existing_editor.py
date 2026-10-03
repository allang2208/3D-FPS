import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('import_assets.py')),
              init_globals={'TREATMENT_CONTAINERS_EXISTING_EDITOR':True})
