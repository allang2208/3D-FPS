"""Save new asset packages independently of the pending native module build."""
import runpy
from pathlib import Path
HERE=Path(__file__).resolve().parent
for directory in (HERE,HERE.parent/'ChimneyR7'):
    for stage in ('prepare_materials.py','import_assets.py'):
        runpy.run_path(str(directory/stage),run_name='__main__')
