"""Add the approved SUPER90 duckbill option without rewriting other weapons."""
import json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];path=P/'Content/ColdSteelData/gunsmith.json'
text=path.read_text(encoding='utf-8-sig');catalog=json.loads(text)
weapon=next(w for w in catalog['weapons'] if w['id']=='ue_super90')
option={'id':'shotgun_duckbill','name':'鸭舌收束器',
    'description':'短扁的深灰钢制壳体向前横向展开，宽口上下收窄，边缘带有细窄倒角。',
    'effects':[{'text':'腰射散布降低25%','benefit':1}],
    'special_effects':['横向散布｜多弹丸沿水平方向呈扇形展开，腰射和开镜均生效；独头弹保持单发直射。'],
    'stats':{'hip_spread_mult':.75}}
rows=weapon['options']['muzzle'];index=next((i for i,row in enumerate(rows) if row['id']==option['id']),None)
if index is None:rows.append(option)
else:rows[index]=option
backup=O/'Before/gunsmith.json';backup.parent.mkdir(exist_ok=True)
if not backup.exists():shutil.copy2(path,backup)
decoder=json.JSONDecoder();pos=text.index('[',text.index('"weapons"'))+1
while True:
    while text[pos].isspace() or text[pos]==',':pos+=1
    if text[pos]==']':raise RuntimeError('SUPER90 entry not located')
    obj,end=decoder.raw_decode(text,pos)
    if obj['id']=='ue_super90':
        indent=text[text.rfind('\n',0,pos)+1:pos]
        replacement=json.dumps(weapon,ensure_ascii=False,indent=2).replace('\n','\n'+indent)
        path.write_text(text[:pos]+replacement+text[end:],encoding='utf-8',newline='\n');break
    pos=end
(O/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_super90','slot':'muzzle','tier':'special',
    'option':option,'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('SHOTGUN_DUCKBILL_CATALOG_SAVED')
