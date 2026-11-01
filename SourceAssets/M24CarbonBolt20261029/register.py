import json,runpy
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1]/'Content/ColdSteelData/gunsmith.json'
if not json.loads((O/'install_receipt.json').read_text())['complete']:raise RuntimeError('Carbon bolt assets must be saved first')
raw=P.read_bytes();data=json.loads(raw)
runpy.run_path(str(O/'catalog.py'))['apply_catalog'](data)
before=O/'gunsmith-before.json'
if not before.exists():before.write_bytes(raw)
if P.read_bytes()!=raw:raise RuntimeError('Catalog changed concurrently; no write performed')
P.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(O/'catalog_receipt.json').write_text(json.dumps({'complete':True,'weapon':'ue_m24','slot':'bolt','id':'m24_carbon_light_bolt',
    'cycle_rate':1.3,'fire_interval_mult':1/1.3,'factory_interval':55/30,'modified_interval':55/30/1.3,'runtime_tested':False},indent=2))
print('M24_CARBON_BOLT_REGISTERED')
