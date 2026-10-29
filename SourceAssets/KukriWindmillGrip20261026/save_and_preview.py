import runpy
from pathlib import Path
root=Path(__file__).resolve().parent
runpy.run_path(str(root/'save_all.py'))
runpy.run_path(str(root/'read_preview.py'))
