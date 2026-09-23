"""One serialized UE write batch for the finished mesh and ten reloads."""
import runpy
from pathlib import Path
folder=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDMagazineFit20260923')
runpy.run_path(str(folder/'import_model.py'))
runpy.run_path(str(folder/'import_animations.py'))
