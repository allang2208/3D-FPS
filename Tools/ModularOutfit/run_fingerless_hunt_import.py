import runpy
from pathlib import Path
HERE=Path('D:/FPS3D/FPSGAME/Tools/ModularOutfit')
runpy.run_path(str(HERE/'inspect_fingerless_hunt_inputs.py'),run_name='__main__')
runpy.run_path(str(HERE/'import_fingerless_hunt_v2.py'),run_name='__main__')
