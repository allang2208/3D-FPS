from pathlib import Path
from runpy import run_path

directory=Path(__file__).resolve().parent
run_path(str(directory.parent/'save_motion.py'))['save'](('Pojun',),directory/'saved-assets.json')
