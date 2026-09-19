"""Apply the V9 fountain palette entry inside the editor owning that asset."""
import importlib.util
from pathlib import Path
import unreal as u

source = Path(__file__).with_name('build_polish_v9_20260919.py')
spec = importlib.util.spec_from_file_location('fountain_polish_v9', source)
author = importlib.util.module_from_spec(spec)
spec.loader.exec_module(author)
author.integrate_palette(u.load_asset(author.ROOT+'/SM_FountainPolishedV9'),
                         u.load_asset(author.ROOT+'/MIC_FountainStoneV9'))
print('FOUNTAIN_V9_PALETTE_SAVED')
