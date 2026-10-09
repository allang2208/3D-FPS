"""Retain the saved WS1 production inputs for later scoped Super90 rebuilds."""
import json,shutil
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'BenelliM4Super9020261006';B=O/'Before'
if not json.loads((O/'import_receipt.json').read_text()).get('completed'):raise RuntimeError('UE material save is incomplete')
for source,target in ((O/'Super90_WS1_Editable.blend',S/'Super90_Gameplay_Editable.blend'),(O/'Exports/SK_Super90_V7.fbx',S/'Exports/SK_Super90_V7.fbx')):
    if not (B/target.name).exists():shutil.copy2(target,B/target.name)
    shutil.copy2(source,target)
print('SUPER90_WS1_PRODUCTION_SOURCE_SAVED')
