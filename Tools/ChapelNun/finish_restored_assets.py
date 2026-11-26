"""Save the final reference groom, then independently read back the saved face LODs."""
from pathlib import Path
import runpy
P=Path('D:/FPS3D/FPSGAME')
runpy.run_path(str(P/'Tools/ChapelNun/save_reference_hair.py'))
runpy.run_path(str(P/'Tools/ChapelNun/capture_restored_face.py'))
