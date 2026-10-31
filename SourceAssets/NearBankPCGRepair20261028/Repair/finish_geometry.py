from pathlib import Path
import runpy,json,unreal as u
R=Path(__file__).resolve().parent;P=R.parent
runpy.run_path(str(P/'build_publish_assets.py'),run_name='__main__')
runpy.run_path(str(P/'install_level.py'),run_name='__main__')
runpy.run_path(str(R/'readback.py'),run_name='__main__')
