"""Add the common shotgun suppressor to the existing SUPER90 muzzle choices."""
import json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
path=P/'Content/ColdSteelData/gunsmith.json'
text=path.read_text(encoding='utf-8-sig');catalog=json.loads(text)
weapon=next(w for w in catalog['weapons'] if w['id']=='ue_super90')
option={'id':'shotgun_suppressor','name':'散弹枪消音器',
    'description':'深灰圆角长壳体，上置出口、下置主体，侧面带有纵向浅筋，独立后座贴合枪管。',
    'effects':[{'text':'后坐力降低25%','benefit':1},
               {'text':'枪械稳定性提高20%','benefit':1},
               {'text':'子弹速度降低15%','benefit':-1},
               {'text':'开镜耗时增加10%','benefit':-1}],
    'special_effects':['消音｜使用专属消音枪声，减弱枪口火光，并缩短敌人听声警戒范围。'],
    'stats':{'recoil_mult':.75,'stability_mult':1.2,'bullet_speed_mult':.85,'ads_percent':.1}}
rows=weapon['options']['muzzle'];index=next((i for i,r in enumerate(rows) if r['id']==option['id']),None)
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
icon=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/muzzle_shotgun_suppressor.png'
if icon.exists():raise RuntimeError('Preserve existing shared icon')
shutil.copy2(O/icon.name,icon)
(O/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_super90','slot':'muzzle','option':option,
    'icon':str(icon),'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('SHOTGUN_SUPPRESSOR_CATALOG_SAVED')
