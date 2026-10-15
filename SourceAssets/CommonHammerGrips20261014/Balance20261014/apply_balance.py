"""Publish the user's three approved stat sets without rerunning asset imports."""
import json,runpy,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
options=runpy.run_path(str(P.parent/'BuildV1/catalog.py'))['OPTIONS']
path=ROOT/'Content/ColdSteelData/common-hammer-grips.json'
before=P/'common-hammer-grips-before.json'
if not before.exists():shutil.copy2(path,before)
data=json.loads(path.read_text(encoding='utf-8-sig'));approved={o['id']:o for o in options}
for option in data['options']:
    if option['id'] in approved:
        source=approved[option['id']]
        option['stats']=source['stats'];option['effects']=source['effects']
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('COMMON_HAMMER_GRIP_BALANCE_SAVED')
