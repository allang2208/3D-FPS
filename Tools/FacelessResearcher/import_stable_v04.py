"""Save the prepared researcher V04 assets with the editor closed."""
from pathlib import Path
TOOLS=Path('D:/FPS3D/FPSGAME/Tools/FacelessResearcher')
for stage in ['import_stable_outfit_v04.py','import_stable_clothing_v04.py','apply_stable_v04.py']:
    path=TOOLS/stage
    exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),{'__name__':'__main__','__file__':str(path)})
