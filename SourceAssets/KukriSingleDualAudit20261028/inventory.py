"""Inventory the installed Kukri body routes; does not alter config or assets."""
from pathlib import Path
import hashlib
import json
from datetime import datetime

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
config_path = ROOT / 'Content/ColdSteelData/player_body.json'
config_bytes = config_path.read_bytes()
config = json.loads(config_bytes.decode('utf-8-sig'))
rows = []
missing_dual = ['Equip', 'Slash1', 'Slash2', 'Thrust', 'Charge', 'Heavy', 'Pommel', 'Recover1', 'Recover2']
for body, section in [('jason', config), ('kaitlin', config['body_variants']['kaitlin'])]:
    for role, asset in section['clips'].items():
        if not (role.startswith('Kukri.FullBody.') or role.startswith('Pistol.KukriCarry.')):
            continue
        package = asset.split('.')[0]
        path = ROOT / 'Content' / (package.removeprefix('/Game/') + '.uasset')
        rows.append(dict(body=body, role=role, asset=asset, path=str(path), exists=path.is_file(),
                         size=path.stat().st_size if path.is_file() else None))
report = dict(recorded=datetime.now().astimezone().isoformat(), config_sha256=hashlib.sha256(config_bytes).hexdigest(),
              assets=rows, counts={body:sum(r['body']==body for r in rows) for body in ['jason','kaitlin']},
              missing_files=[r['asset'] for r in rows if not r['exists']],
              missing_dedicated_dual_roles={body:[role for role in missing_dual if 'Kukri.FullBody.Dual.'+role not in section['clips']]
                  for body,section in [('jason',config),('kaitlin',config['body_variants']['kaitlin'])]},
              runtime_tested=False, visuals_reviewed=False)
(OUT/'inventory.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='assets'},ensure_ascii=False))
