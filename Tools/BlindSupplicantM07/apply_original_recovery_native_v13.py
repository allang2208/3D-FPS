"""Switch native M07 defaults after V13 packages have actually saved."""
import json
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME')
receipt = json.loads((ROOT/'SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryOriginalV13/ue_delivery_v13.json').read_text(encoding='utf-8-sig'))
if not receipt.get('saved'):
    raise RuntimeError('Save V13 assets before switching native defaults.')
path = ROOT/'Source/FPSGAME/Monsters/BlindSupplicantMonster.cpp'
source = path.read_text(encoding='utf-8-sig')
source = source.replace('SK_M07_OriginalV12.SK_M07_OriginalV12', 'SK_M07_OriginalV13.SK_M07_OriginalV13')
source = source.replace('/AnimationsOriginalV11/', '/AnimationsOriginalV13/')
source = source.replace('/AnimationsRunningV12/', '/AnimationsOriginalV13/')
path.write_text(source, encoding='utf-8')
print('M07_V13_SAVED_MODEL_AND_TWELVE_ACTION_NATIVE_DEFAULTS_UPDATED', flush=True)
