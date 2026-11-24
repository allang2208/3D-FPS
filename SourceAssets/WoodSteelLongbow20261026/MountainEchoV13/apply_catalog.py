"""Install only this owned option into the latest shared catalog."""
from pathlib import Path
import json,hashlib
P=Path(__file__).parent;ROOT=P.parents[2]
path=ROOT/'Content/ColdSteelData/bow-gunsmith.json'
raw=path.read_bytes();catalog=json.loads(raw)
proposal=json.loads((P.parent/'MountainEchoStringConceptV12/design.json').read_text(encoding='utf-8'))
effects=list(proposal['special_effects_proposed'])
effects[0]+='切换武器、拆下弓弦或死亡时清空。'
effects[1]='光柱回响｜3层弦鸣时，下一次满弓射击消耗全部层数。0.18秒后沿原方向补出一支弦影箭，造成原箭物理伤害的80%。装备极光弓体时，弦影化为蓝色光束，按原箭的魔法伤害结算。弦影不额外耗箭或体力。'
effects[2]='弦影｜沿用原箭的暴击结果。触发回响的射击及弦影均不积攒弦鸣。弦影不复制贯穿、元素或照明效果，不可回收，也不额外获得技能修炼进度。'
mesh='/Game/Weapons/WoodSteelLongbow20261026/BeamString20261121/SK_Highland_BeamString.SK_Highland_BeamString'
row={
 'id':'highland_mountain_echo','name':'光柱弓弦',
 'description':'金白色光束连接两端弦扣，满弓命中积攒弦鸣，满层后的下一次满弓射击引出弦影箭。',
 'appearance':'细亮的弦身随开弓拉紧，两端保留银套，中央炭黑护弦旁的三道山纹随弦鸣逐层点亮。',
 'stats':proposal['stats_proposed'],'special_effects':effects,
 'visual':{'bow_part_string_mesh':mesh,'bow_part_string_rods':0,'bow_part_string_material':'',
           'bow_part_string_scale':1.0,'bow_part_string_location_cm':'0,0,0','bow_part_string_rotation_deg':'0,0,0','bow_part_string_hide_slot':''}
}
column=next(c for c in catalog['columns'] if c['key']=='string')
prior=next((i for i,o in enumerate(column['options']) if o['id']==row['id']),None)
if prior is None:column['options'].append(row)
else:column['options'][prior]=row
backup=P/'bow-gunsmith.before.json'
if not backup.exists():backup.write_bytes(raw)
if path.read_bytes()!=raw:raise RuntimeError('Catalog changed while preparing this option; rerun against the latest file')
path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'catalog-entry.json').write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'catalog-receipt.json').write_text(json.dumps({'option':row['id'],'slot':'string','scope':'bows','tier':'Special',
 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'gameplay_tested':False},indent=2),encoding='utf-8')
print('MOUNTAIN_ECHO_CATALOG_INSTALLED')
