"""Install only the two armrest exits through the scoped furniture publisher."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('publish_chair_reuse.py')),
               init_globals={'FURNITURE_REVISION': 'ArmrestExit20261024'})
