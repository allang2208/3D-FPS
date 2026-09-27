import runpy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME/Tools/ModularOutfit')
for name in ('import_fingerless_skin_companions.py','publish_coupled_fingerless.py','read_final_fingerless_clearance.py'):
    runpy.run_path(str(P/name))
