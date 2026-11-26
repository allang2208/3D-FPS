"""Entry point for the frozen Kaitlin third-person weapon contact repair."""
import runpy
from pathlib import Path
import sys
base = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinWeaponContacts20261024/ContactFitV1')
sys.path.insert(0, str(base))
runpy.run_path(str(base / Path(__file__).name), run_name='__main__')