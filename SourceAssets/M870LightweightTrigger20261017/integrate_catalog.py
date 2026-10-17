"""Update only the M870 JSON block and keep all concurrent catalog entries."""
import json,runpy
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];path=P/'Content/ColdSteelData/gunsmith.json'
raw=path.read_bytes();text=raw.decode('utf-8-sig');decoder=json.JSONDecoder()
config=runpy.run_path(str(O/'catalog_option.py'))
pos=text.index('[',text.index('"weapons"'))+1
while True:
    while text[pos].isspace() or text[pos]==',':pos+=1
    if text[pos]==']':raise RuntimeError('M870 entry missing')
    weapon,end=decoder.raw_decode(text,pos)
    if weapon['id']=='ue_m870':break
    pos=end
config['merge'](weapon)
indent=text[text.rfind('\n',0,pos)+1:pos]
replacement=json.dumps(weapon,ensure_ascii=False,indent=2).replace('\n','\n'+indent)
backup=O/'Before/gunsmith.json';backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():backup.write_bytes(raw)
if path.read_bytes()!=raw:raise RuntimeError('Catalog changed during merge')
path.write_text(text[:pos]+replacement+text[end:],encoding='utf-8',newline='\n')
receipt={'weapon':'ue_m870','slot':'trigger','tier':'special','option':config['OPTION'],
         'base_interval_seconds':weapon['base']['fire_interval'],
         'interval_with_kit_seconds':weapon['base']['fire_interval']*config['OPTION']['stats']['fire_interval_mult'],
         'icon':'trigger_m1911_lightweight_fast','runtime_tested':False}
(O/'catalog_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('M870_LIGHTWEIGHT_TRIGGER_CATALOG_SAVED')
