from pathlib import Path
import runpy,sys,gc
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
runpy.run_path(str(R/'publish.py'))
# The publication function has released all Python world references before reloading.
gc.collect()
runpy.run_path(str(R/'capture_after.py'))
