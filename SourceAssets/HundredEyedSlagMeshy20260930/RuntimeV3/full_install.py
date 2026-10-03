from pathlib import Path
import runpy
folder=Path(__file__).resolve().parent
runpy.run_path(str(folder/'install_runtime.py'))['install']('meshes')
runpy.run_path(str(folder/'finish_install.py'),run_name='__main__')
