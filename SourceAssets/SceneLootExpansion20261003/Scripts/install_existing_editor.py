import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('install_scenes.py')),init_globals={'SCENE_LOOT_EXISTING_EDITOR_INSTALL':True})
