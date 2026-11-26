"""Export the new authored source only. No UE operations or preview renders."""
import runpy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
runpy.run_path(str(P/'Tools/RangerLeatherPants/export.py'),run_name='__main__',init_globals={'ROOT_OVERRIDE':str(P/'SourceAssets/RangerLeatherPants20261021/RealisticCutV3')})
