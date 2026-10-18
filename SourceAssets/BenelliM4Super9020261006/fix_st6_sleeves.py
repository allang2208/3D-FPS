"""ST6 original sleeves + native-body fabric; the former torso shell is retired."""
import runpy
from pathlib import Path
TASK=Path(__file__).parent.parent/'ST6Reset20261017'
runpy.run_path(str(TASK/'author_sleeves.py'),run_name='__main__')
