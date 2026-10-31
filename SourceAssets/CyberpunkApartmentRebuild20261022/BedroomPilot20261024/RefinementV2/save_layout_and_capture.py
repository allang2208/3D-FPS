from pathlib import Path
import runpy,gc
R=Path(__file__).resolve().parent
runpy.run_path(str(R/'install_level.py'))['main']()
gc.collect()
runpy.run_path(str(R/'capture_after.py'))
