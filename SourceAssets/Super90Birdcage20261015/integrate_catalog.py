"""Publish the authorized birdcage option without replacing the choke."""
import json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
path=P/'Content/ColdSteelData/gunsmith.json'
text=path.read_text(encoding='utf-8-sig');catalog=json.loads(text)
weapon=next(w for w in catalog['weapons'] if w['id']=='ue_super90')
option={'id':'shotgun_birdcage_flash_hider','name':'鸟笼消焰器',
        'description':'短筒式深灰金属外壳，纵向开槽与环形前缘，后端接座贴合枪管。',
        'effects':[{'text':'后坐力降低15%','benefit':1},{'text':'腰射随机散布减少15%','benefit':1}],
        'special_effects':['消焰｜减弱枪口火光及瞬时照明。'],
        'stats':{'recoil_mult':.85,'hip_spread_mult':.85}}
rows=weapon['options']['muzzle']
index=next((i for i,r in enumerate(rows) if r['id']==option['id']),None)
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
icon=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/muzzle_shotgun_birdcage_flash_hider.png'
if icon.exists():raise RuntimeError('Preserve existing shared icon')
shutil.copy2(O/icon.name,icon)
(O/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_super90','slot':'muzzle','option':option,
    'icon':str(icon),'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('BIRDCAGE_CATALOG_SAVED')
