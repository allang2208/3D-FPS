"""Set bow-owned combat traits while retaining fresh movement/attachment edits."""
import json
from pathlib import Path
P=Path(__file__).parent;ROOT=P.parents[1]
path=ROOT/'Content/ColdSteelData/bows.json'
data=json.loads(path.read_text(encoding='utf-8-sig'));bow=data['bow_dark']
bow['critDamageBonus']=.5
bow['bow_traits_revision']=max(1,int(bow.get('bow_traits_revision',0)))
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
path=ROOT/'Content/ColdSteelData/bow-gunsmith.json'
data=json.loads(path.read_text(encoding='utf-8-sig'))
weapon=next(w for w in data['weapons'] if w['id']=='bow_dark')
# Keep existing gameplay copy, combining the two purely descriptive construction lines.
traits=weapon.setdefault('traits',[])
old=('整根弓胎 · 独立缠带','五槽改造 · 箭矢独立')
traits[:]=[t for t in traits if t.get('text') not in old]
additions=[
    {'icon':'neutral','text':'整根弓胎、独立缠带与箭矢，支持五槽改造'},
    {'icon':'special','text':'暴击伤害加成 +50%，与暴击技能加成相加后单次结算'},
    {'icon':'mechanic','text':'无声射击：拉弓、放箭与箭矢命中不会通过声音引起怪物警觉'},
    {'icon':'special','text':'一箭直接击杀不会触发周围怪物警报；未击杀仍会引起目标反应，已暴露的目标不会脱战'},
]
for row in additions:
    if not any(t.get('text')==row['text'] for t in traits):traits.append(row)
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(P/'install-receipt.json').write_text(json.dumps({'critDamageBonus':.5,
    'bow_traits_revision':bow['bow_traits_revision'],'traits':traits,
    'audio':'Retain local draw/release sounds; no AI hearing event',
    'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf8')
print('BOW_STEALTH_TRAITS_SAVED')
