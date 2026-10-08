"""Save just the revised ground material and feathered motes."""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parent
runpy.run_path(str(ROOT / 'author_soft_ground.py'), run_name='__main__')
runpy.run_path(str(ROOT.parent / 'RisingMotes/author_rising_motes.py'), run_name='__main__')
