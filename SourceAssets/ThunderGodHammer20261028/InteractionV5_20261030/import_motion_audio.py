"""One serialized editor batch, limited to the two takes and new charge sound."""
from pathlib import Path
import runpy
S=Path(__file__).resolve().parent.parent
for folder in ('JiLeiMotionV5','JiLeiChargeAudioV1','GuanLeiReturnC8'):
 runpy.run_path(str(S/folder/'import_assets.py'),run_name='__main__')
print('JI_LEI_V5_MOTION_AND_AUDIO_SAVED')
