import sys,runpy,gc
from pathlib import Path
import unreal as u
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R))
runpy.run_path(str(R/'install_level.py'),run_name='__main__')
gc.collect();u.SystemLibrary.collect_garbage()
runpy.run_path(str(R/'capture_after.py'),run_name='__main__')
runpy.run_path(str(R/'read_saved_assets.py'),run_name='__main__')
