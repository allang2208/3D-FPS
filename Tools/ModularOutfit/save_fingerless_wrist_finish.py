import runpy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME/Tools/ModularOutfit')
runpy.run_path(str(P/'import_fingerless_skin_companions.py'))
runpy.run_path(str(P/'publish_coupled_fingerless.py'))
runpy.run_path(str(P/'read_coupled_clearance_meshes.py'))
