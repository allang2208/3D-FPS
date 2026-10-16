"""Publish the new shared shotgun identity to the currently supported SUPER90."""
import json
import shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
path=P/'Content/ColdSteelData/gunsmith.json'
text=path.read_text(encoding='utf-8-sig')
catalog=json.loads(text)
weapon=next(w for w in catalog['weapons'] if w['id']=='ue_super90')
option={'id':'shotgun_choke','name':'收束器',
        'description':'方形深灰金属外壳，圆角切边与分段接缝，沿枪管前端安装。',
        'effects':[{'text':'弹丸散布减少35%','benefit':1}],
        'stats':{'pellet_spread_mult':.65}}
rows=weapon['options']['muzzle']
existing=next((i for i,r in enumerate(rows) if r['id']==option['id']),None)
if existing is None:rows.append(option)
else:rows[existing]=option
backup=O/'Before/gunsmith.json';backup.parent.mkdir(exist_ok=True)
if not backup.exists():shutil.copy2(path,backup)
# Replace only this weapon object, preserving all other concurrently edited rows.
decoder=json.JSONDecoder();array_start=text.index('[',text.index('"weapons"'))
pos=array_start+1
while True:
    while text[pos].isspace() or text[pos]==',':pos+=1
    if text[pos]==']':raise RuntimeError('SUPER90 entry not located')
    obj,end=decoder.raw_decode(text,pos)
    if obj['id']=='ue_super90':
        line=text.rfind('\n',0,pos)+1;indent=text[line:pos]
        replacement=json.dumps(weapon,ensure_ascii=False,indent=2).replace('\n','\n'+indent)
        path.write_text(text[:pos]+replacement+text[end:],encoding='utf-8',newline='\n')
        break
    pos=end
icon=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/muzzle_shotgun_choke.png'
if icon.exists():raise RuntimeError('Shared icon destination is already occupied')
shutil.copy2(O/'muzzle_shotgun_choke.png',icon)
(O/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_super90','slot':'muzzle','option':option,
    'icon':str(icon),'saved_by_existing_gunsmith_parts':True,'gameplay_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('SHOTGUN_CHOKE_CATALOG_SAVED')
