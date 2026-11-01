import json,runpy
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1]/'Content/ColdSteelData/gunsmith.json'
if not json.loads((O/'install_receipt.json').read_text())['complete']:raise RuntimeError('Rear grip assets must be saved first')
raw=P.read_bytes();data=json.loads(raw);runpy.run_path(str(O/'catalog.py'))['apply_catalog'](data)
if not (O/'gunsmith-before.json').exists():(O/'gunsmith-before.json').write_bytes(raw)
if P.read_bytes()!=raw:raise RuntimeError('Concurrent catalog change; retained')
P.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(O/'catalog_receipt.json').write_text(json.dumps(dict(complete=True,weapon='ue_m24',slot='reargrip',
    variants=['phantom_reargrip','stable_antislip_reargrip','balanced_reargrip'],shared_stats_from='ue_m4a1',runtime_tested=False),indent=2))
print('M24_REAR_GRIPS_REGISTERED')
