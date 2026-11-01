"""Publish exactly this revision's assets, in one serialized background batch."""
from pathlib import Path
import json,runpy
P=Path(__file__).resolve().parent;S=P.parent
steps=[('JiLeiMotionV5','import_assets.py','import_receipt.json','complete'),
       ('JiLeiChargeAudioV1','import_assets.py','import_receipt.json','saved'),
       ('GuanLeiReturnC8','import_assets.py','import_receipt.json','complete'),
       ('GuanLeiReturnC8','import_icon.py','publication_receipt.json','complete')]
for folder,script,receipt,key in steps:
 path=S/folder/receipt
 # Resume saved work, never reimport an unknown partial batch blindly.
 if path.exists() and json.loads(path.read_text(encoding='utf-8-sig')).get(key):continue
 runpy.run_path(str(S/folder/script),run_name='__main__')
(P/'asset_receipt.json').write_text(json.dumps({'complete':True,
 'model':'GuanLeiReturnC8','motion':'JiLeiMotionV5','audio':'JiLeiChargeAudioV1',
 'production_icon_saved':True,'tier':'special','gameplay_tested':False},indent=2),encoding='utf-8')
print('THUNDER_HAMMER_INTERACTION_V5_ASSETS_SAVED')
