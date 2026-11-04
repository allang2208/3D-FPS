"""Replace only the active Rift Piercer description; preserve concurrent catalog work."""
from pathlib import Path
import json,runpy
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
source=runpy.run_path(str(P.parent/'install_catalog.py'))['OPTION']
path=ROOT/'Content/ColdSteelData/melee-gunsmith.json';before=path.read_bytes()
data=json.loads(before.decode('utf-8-sig'))
entry=next(o for c in data['columns'] if c['key']=='blade_1' for o in c['options'] if o['id']=='rift_piercer')
entry['special_effects']=source['special_effects']
backup=P/'BeforeSource/melee-gunsmith.json'
if not backup.exists():backup.write_bytes(before)
if path.read_bytes()!=before:raise RuntimeError('Concurrent catalog edit; preserve it')
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('INSTANT_THRUST_DESCRIPTION_PUBLISHED')
