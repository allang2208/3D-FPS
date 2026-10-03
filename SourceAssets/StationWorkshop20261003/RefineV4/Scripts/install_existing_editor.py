"""Import and save through a single existing editor bridge batch."""
import runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for name in ('import_assets.py','install_scenes.py'):
    runpy.run_path(str(ROOT/'Scripts'/name),init_globals={'STATION_FIT_EXISTING_EDITOR':True})
