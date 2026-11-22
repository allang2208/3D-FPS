import runpy
from pathlib import Path
root=Path('F:\\FPSGAMEData\\ArtProduction\\M249Orpind20261107\\ApprovedRecovery20261121\\SurfaceHost\\SourceAssets\\M249Orpind20261107\\Repair13')
runpy.run_path(str(root/'replay.py'),run_name='__main__')
