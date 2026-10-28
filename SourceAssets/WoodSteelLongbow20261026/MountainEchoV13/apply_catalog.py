"""Install only this owned option into the latest shared catalog."""
from pathlib import Path
import json,hashlib
P=Path(__file__).parent;ROOT=P.parents[2]
path=ROOT/'Content/ColdSteelData/bow-gunsmith.json'
raw=path.read_bytes();catalog=json.loads(raw)
proposal=json.loads((P.parent/'MountainEchoStringConceptV12/design.json').read_text(encoding='utf-8'))
effects=list(proposal['special_effects_proposed'])
effects[0]+='切换武器、拆下弓弦或死亡时清空。'
effects[1]+='触发回响的射击不积攒弦鸣。'
effects[2]+='弦影不可回收，不额外获得技能修炼进度。'
mesh='/Game/Weapons/WoodSteelLongbow20261026/MountainEchoV13/SK_Highland_MountainEchoString.SK_Highland_MountainEchoString'
row={
 'id':'highland_mountain_echo','name':'山鸣弓弦','weapons':['bow_woodsteel'],
 'description':'高地长弓专属弓弦，银灰纤维与石墨色绳股交编，细金丝穿过弦身。',
 'appearance':'柔性弦环配短银套，炭黑护弦上方缀有三道山纹。',
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
(P/'catalog-receipt.json').write_text(json.dumps({'option':row['id'],'weapon':'bow_woodsteel','tier':'Legendary',
 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'gameplay_tested':False},indent=2),encoding='utf-8')
print('MOUNTAIN_ECHO_CATALOG_INSTALLED')
