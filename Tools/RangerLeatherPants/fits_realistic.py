"""Apply existing native boot fit envelopes to all layers of RealisticCutV3."""
import runpy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
runpy.run_path(str(P/'Tools/RangerLeatherPants/fits.py'),run_name='__main__',init_globals={'ROOT_OVERRIDE':str(P/'SourceAssets/RangerLeatherPants20261021/RealisticCutV3')})
