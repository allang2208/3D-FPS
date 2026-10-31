import runpy,sys
from pathlib import Path
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
runpy.run_path(str(R/'final_assets.py'),run_name='__main__')
runpy.run_path(str(R/'publish_and_capture.py'),run_name='__main__')
