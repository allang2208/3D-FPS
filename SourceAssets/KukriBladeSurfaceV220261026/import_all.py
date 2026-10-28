"""Apply surface and icon revisions within one UE bridge mutex batch."""
import runpy
from pathlib import Path
P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/KukriBladeSurfaceV220261026')
runpy.run_path(str(P/'import_surface.py'),run_name='__main__')
runpy.run_path(str(P/'import_icons.py'),run_name='__main__')
