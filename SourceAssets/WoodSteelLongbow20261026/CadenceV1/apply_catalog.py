"""Merge just this attachment/status into the latest catalogs, retaining parallel work."""
from pathlib import Path
import json,hashlib
P=Path(__file__).parent;ROOT=P.parents[2]
proposal=json.loads((P.parent/'CadenceStringConcept20261028/design.json').read_text(encoding='utf-8'))
mesh='/Game/Weapons/WoodSteelLongbow20261026/CadenceV1/SK_Highland_CadenceString.SK_Highland_CadenceString'
row={'id':'highland_cadence','name':'疾律弓弦','weapons':['bow_woodsteel'],
 'description':'高地长弓专属弓弦，深蓝与石墨纤维交编银丝，以细密缠线标记节律。',
 'appearance':'柔性弦环、平整护弦和五组银金缠线，合拍时泛起白金辉光。',
 'stats':{'rhythm_window_bonus':1.0},
 'special_effects':[
  '律动｜节拍放箭获得1层律动，每层拉弓速度+20%，最多5层（满层+100%），持续6秒；再次触发刷新持续时间，无需命中目标。',
  '合拍｜律动达到5层后，腰射扩散−50%、物理伤害+20%，从后续箭矢生效。满层期间成功射出任意手动箭均视为节拍成功，刷新6秒持续时间并获得原节拍加速，不消耗层数，无需命中目标。',
  '失拍｜未满层时非节拍箭射出后，或持续时间结束时清空律动。取消收弓不刷新持续时间；切换武器、拆下弓弦或死亡时清空。'],
 'visual':{'bow_part_string_mesh':mesh,'bow_part_string_rods':0,'bow_part_string_material':'',
 'bow_part_string_scale':1.,'bow_part_string_location_cm':'0,0,0','bow_part_string_rotation_deg':'0,0,0','bow_part_string_hide_slot':''}}
def merge(path,change):
 raw=path.read_bytes();data=json.loads(raw);change(data)
 backup=P/(path.stem+'.before.json')
 if not backup.exists():backup.write_bytes(raw)
 if path.read_bytes()!=raw:raise RuntimeError('Catalog changed; resume from its current contents: '+str(path))
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return hashlib.sha256(path.read_bytes()).hexdigest()
def bow(data):
 options=next(c for c in data['columns'] if c['key']=='string')['options']
 index=next((i for i,o in enumerate(options) if o['id']==row['id']),None)
 if index is None:options.append(row)
 else:options[index]=row
def status(data):
 entry={'type':'bowCadence','icon':'cadence','name':'律动','kind':'buff','group':'triggered','color':'#8FBFD6',
 'description':'疾律弓弦：节拍判定窗口+100%；节拍放箭叠加律动，每层拉弓速度+20%，最多5层（满层+100%），持续6秒。满层腰射扩散−50%、物理伤害+20%，成功射出任意手动箭即触发节拍并刷新6秒。未满层非节拍放箭、超时、切换武器或死亡时清空。'}
 options=data['effects'];index=next((i for i,o in enumerate(options) if o['type']==entry['type']),None)
 if index is None:options.append(entry)
 else:options[index]=entry
receipt={'bow_catalog':merge(ROOT/'Content/ColdSteelData/bow-gunsmith.json',bow),
 'status_catalog':merge(ROOT/'Content/ColdSteelData/status_effects.json',status),'gameplay_tested':False}
(P/'catalog-entry.json').write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'catalog-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('CADENCE_CATALOG_INSTALLED')
