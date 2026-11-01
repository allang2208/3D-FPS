import json,runpy
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1]/'Content/ColdSteelData/gunsmith.json'
if not json.loads((O/'install_receipt.json').read_text())['complete']:raise RuntimeError('Save chassis assets before catalog publication')
raw=P.read_bytes();data=json.loads(raw);runpy.run_path(str(O/'catalog.py'))['apply_catalog'](data)
before=O/'gunsmith-before.json'
if not before.exists():before.write_bytes(raw)
if P.read_bytes()!=raw:raise RuntimeError('Catalog changed concurrently; retained')
P.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(O/'catalog_receipt.json').write_text(json.dumps(dict(complete=True,weapon='ue_m24',slot='body',id='m24_advanced_action',runtime_tested=False),indent=2))
print('M24_ADVANCED_ACTION_CATALOG_SAVED')
