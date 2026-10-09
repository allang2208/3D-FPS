"""Import the prepared M-05 state extension and save the original entry."""
from pathlib import Path
TOOLS=Path('D:/FPS3D/FPSGAME/Tools/FacelessResearcher')
for stage in ['import_states_outfit_v05.py','import_states_clothing_v05.py','apply_states_v05.py']:
    path=TOOLS/stage
    exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),{'__name__':'__main__','__file__':str(path)})
