from pathlib import Path
import runpy

here = Path(__file__).resolve().parent
install = runpy.run_path(str(here.parent / 'CommonMods/install_legendary_blade.py'))['install']
install(here, 'HollowBlade', 'hollow_blade', 'HollowHost')
print('HOLLOW_BLADE_ASSETS_SAVED')
