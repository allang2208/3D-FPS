import runpy
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/LMG20120260927/Skin07')
runpy.run_path(str(O/'import_animations.py'), run_name='__main__')
runpy.run_path(str(O/'read_installed_skin_after.py'), run_name='__main__')
print('LMG201_SKIN07_IMPORT_AND_READBACK_COMPLETE')