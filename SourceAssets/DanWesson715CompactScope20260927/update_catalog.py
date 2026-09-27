"""Upsert just the two requested options, preserving existing/parallel options."""
import json
from pathlib import Path
root=Path(__file__).parents[2];path=root/'Content/ColdSteelData/gunsmith.json'
data=json.loads(path.read_text(encoding='utf-8-sig'))
w=next(x for x in data['weapons'] if x['id']=='ue_dan_wesson715')
options={
 'reargrip':dict(id='dw715_compact_grip',name='轻量紧凑握把',
    description='收紧外露后跟的轻量复合握把，保留安装颈部与主要握持轮廓；抬枪更轻快，但稳定瞄准能力有所下降。',
    effects=[dict(text='开镜耗时减少10%',benefit=1),dict(text='枪械稳定性降低10%',benefit=-1)],
    stats={'ads_percent':-.10,'stability_mult':.90}),
 'optic':dict(id='dw715_handgun_scope_2x',name='长出瞳 2× 手枪瞄准镜',
    description='适配左轮持握距离的固定倍率手枪镜，采用细十字与粗边分划、独立镜座；便于辨识远处目标，但开镜更慢、镜内视野更窄。',
    effects=[dict(text='瞄具倍率2×',benefit=1),dict(text='开镜耗时增加15%',benefit=-1)],
    stats={'ads_percent':.15})}
for slot,option in options.items():
    if slot not in w['allowed']:w['allowed'].append(slot)
    entries=w['options'].setdefault(slot,[])
    existing=next((i for i,x in enumerate(entries) if x['id']==option['id']),None)
    if existing is None:entries.append(option)
    else:entries[existing]=option
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('DW715 compact grip and fixed 2x handgun optic catalog saved')
