"""Export AtelierFinishV2 without regenerating previews or running checks."""
import runpy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/RangerLeatherPants20261021/AtelierFinishV2'
runpy.run_path(str(P/'Tools/RangerLeatherPants/export.py'),run_name='__main__',init_globals={'ROOT_OVERRIDE':str(R)})
