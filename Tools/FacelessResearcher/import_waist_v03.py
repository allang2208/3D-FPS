"""Background mesh, animation-curve and blueprint save for M-05 V03."""
from pathlib import Path
TOOLS=Path('D:/FPS3D/FPSGAME/Tools/FacelessResearcher')
for stage in ['import_waist_outfit_v03.py','import_waist_clothing_v03.py','apply_waist_v03.py']:
    path=TOOLS/stage
    exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'))
