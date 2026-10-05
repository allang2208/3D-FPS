"""Save the V19 corpse repair followed by the V20 whirlwind range update."""
from pathlib import Path
import runpy

scripts = Path(__file__).resolve().parent
runpy.run_path(str(scripts / 'import_xpbd_corpse_v19.py'), run_name='__main__')
runpy.run_path(str(scripts / 'import_whirlwind_range_v20.py'), run_name='__main__')
