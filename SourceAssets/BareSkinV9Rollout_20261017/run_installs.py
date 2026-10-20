import os, runpy
from pathlib import Path
R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9Rollout_20261017')
for b in os.environ.get('V9R_BATCHES', 'batch1').split(','):
    os.environ['V9R_BATCH'] = b
    runpy.run_path(str(R / 'install_batch.py'), run_name='__main__')
print('V9R_INSTALLS_COMPLETE', flush=True)

