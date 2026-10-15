"""Stage an untrusted candidate; only native replay can authorize installation."""
import copy
import json
from pathlib import Path

project = Path('D:/FPS3D/FPSGAME')
root = project/'SourceAssets/HeQueBoss20261014/DungeonE2E/Records'
catalog_path = project/'Saved/DungeonRoutingFix20260927/heque-dungeon-saved-20261015-catalog.json'
catalog = json.loads(catalog_path.read_text(encoding='utf-8-sig'))
report = json.loads((catalog_path.parent/'heque-dungeon-saved-20261015.json').read_text(encoding='utf-8-sig'))[0]
bank = copy.deepcopy(catalog['facility_flow']['layout_bank'])
old = bank['contract_sha1']
bank['contract_sha1'] = report['catalog_contract_sha1']
bank['native_replay_pending'] = True
bank['revalidation_source_contract'] = old
(root/'layout-bank-candidate.json').write_text(json.dumps(bank,ensure_ascii=False,separators=(',',':')),encoding='utf8')
cases = []
for index, (key, entry) in enumerate(sorted(bank['entries'].items())):
    cases.append(dict(id=key,seed=entry['source_seed'],themes=sum([entry['route_pairs'][f'Route{r}'] for r in range(1,4)],[])))
(root/'layout-bank-cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf8')
(root/'catalog-before.json').write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')),encoding='utf8')
print(json.dumps(dict(entries=len(cases),old_contract=old,current_contract=bank['contract_sha1'])))
