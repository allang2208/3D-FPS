import runpy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
for name in ('read_saved.py','resave_sections.py'):
    runpy.run_path(str(P/'Tools/BlueMageAudit'/name),run_name='__main__')
