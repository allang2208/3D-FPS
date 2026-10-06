"""Publish common device choices only to the RSH tactical slot."""
import copy,json,re
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1]
receipt=json.loads((O/'import_receipt.json').read_text())
if not receipt.get('complete'):raise RuntimeError('Asset import has not completed')
path=P/'Content/ColdSteelData/gunsmith.json';raw=path.read_bytes();text=raw.decode('utf-8-sig')
catalog=json.loads(text)
donor=next(w for w in catalog['weapons'] if w['id']=='ue_dan_wesson715')
choices=[copy.deepcopy(o) for o in donor['options']['tactical'] if o['id'] in ('laser','flashlight')]
decoder=json.JSONDecoder();pos=text.index('[',text.index('"weapons"'))+1
while True:
    while text[pos].isspace() or text[pos]==',':pos+=1
    weapon,end=decoder.raw_decode(text,pos)
    if weapon['id']=='ue_rsh12':break
    pos=end
if 'tactical' not in weapon['allowed']:weapon['allowed'].append('tactical')
for choice in choices:
    existing=next((v for v in weapon['options']['tactical'] if v['id']==choice['id']),None)
    if existing is None:weapon['options']['tactical'].append(choice)
    else:existing.update(choice)
indent=re.search(r'[^\S\n]*$',text[:pos]).group()
replacement=json.dumps(weapon,ensure_ascii=False,indent=2).replace('\n','\n'+indent)
backup=O/'Before/gunsmith.json';backup.parent.mkdir(exist_ok=True)
if not backup.exists():backup.write_bytes(raw)
if path.read_bytes()!=raw:raise RuntimeError('Catalog changed during publication')
path.write_bytes((text[:pos]+replacement+text[end:]).encode('utf8'))
(O/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_rsh12','slot':'tactical','choices':choices,
    'selection':'one device per weapon; foregrip remains independent','shared_icons':receipt['icons'],
    'other_weapons_changed':False,'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf8')
print('RSH_TACTICAL_CATALOG_SAVED',flush=True)
