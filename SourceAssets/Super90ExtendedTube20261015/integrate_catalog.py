"""Add only the SUPER90 magazine option; preserve concurrent catalog entries."""
import json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];path=P/'Content/ColdSteelData/gunsmith.json'
text=path.read_text(encoding='utf-8-sig');catalog=json.loads(text)
weapon=next(w for w in catalog['weapons'] if w['id']=='ue_super90')
option={'id':'super90_extended_tube','name':'加长管式弹仓',
    'description':'细长深灰管体沿原厂弹仓向前延伸，端部保留原厂端帽的轮廓和环纹。',
    'effects':[{'text':'弹仓容量增加3发','benefit':1},{'text':'开镜耗时增加10%','benefit':-1}],
    'special_effects':['组合适配｜与收束器、散弹枪消音器同时安装时，自动使用兼容外壳。'],
    'stats':{'mag_delta':3,'ads_percent':.1}}
rows=weapon['options']['magazine'];index=next((i for i,row in enumerate(rows) if row['id']==option['id']),None)
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
(O/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_super90','slot':'magazine','option':option,
    'tier':'special','runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('SUPER90_EXTENDED_TUBE_CATALOG_SAVED')
