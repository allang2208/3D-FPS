"""Add only the ASH cheek rest option and its cook directory."""
import json
from pathlib import Path
ROOT=Path(__file__).parents[2];p=ROOT/'Content/ColdSteelData/gunsmith.json'
text=p.read_text(encoding='utf-8-sig');marker=text.index('"id": "ue_ash12"');start=text.rfind('{',0,marker)
ash,length=json.JSONDecoder().raw_decode(text[start:])
if 'stock' not in ash['allowed']:ash['allowed'].append('stock')
options=ash['options'].setdefault('stock',[])
if not any(o['id']=='false' for o in options):
 options.insert(0,{'id':'false','name':'原厂后托','description':'保留 ASH-12 原厂后托，不安装托腮板。','effects':[],'stats':{}})
option={'id':'ash12_cheek_rest','name':'ASH-12 贴合式托腮板','description':'ASH-12 专用低矮托腮板，包覆原厂后托顶部，采用软质接触垫与两侧金属固定片。','effects':[],'stats':{}}
for i,o in enumerate(options):
 if o['id']==option['id']:options[i]=option;break
else:options.append(option)
indent=len(text[:start].rsplit('\n',1)[-1]);replacement=json.dumps(ash,ensure_ascii=False,indent=2).replace('\n','\n'+' '*indent)
p.write_text(text[:start]+replacement+text[start+length:],encoding='utf-8')
ini=ROOT/'Config/DefaultGame.ini';txt=ini.read_text(encoding='utf-8-sig')
line='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/ASH12/CheekRest20260919")'
if line not in txt:
 marker='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/ASH12/UniversalAttachments20260919")'
 if marker not in txt:raise RuntimeError('Locate ASH cook section before writing')
 ini.write_text(txt.replace(marker,marker+'\n'+line,1),encoding='utf-8')
print('ASH12_CHEEK_REST_CATALOG_INSTALLED')
