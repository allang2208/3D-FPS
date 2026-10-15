"""Add six ingredient definitions and complete medical/ecology search bindings.
Does not register recipes, consumption effects, a crafting station or a new UI.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,shutil
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];DATA=PROJECT/'Content/ColdSteelData'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def backup(p):
 dest=ROOT/'Before'/p.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True)
 if not dest.exists():shutil.copy2(p,dest)
def write(p,data):
 backup(p);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
installed=read(ROOT/'Receipts/installation.json')
if installed['stage']!='assets_installed':raise RuntimeError('Finish asset installation first')
spec=read(ROOT/'model_manifest.json');icons=read(ROOT/'presentation.json');meshes=read(ROOT/'Receipts/ue-import.json')
if icons['stage']!='inventory_icons_saved':raise RuntimeError('Finish six requested icons first')
DESC={
 'BaseFluid':'设施药剂室精制并封存的调配基液，厚壁刻度瓶与防拆封口保护着清澈液体。作为药剂调配的通用基底保存，适合与不同活性原料配合；不可直接饮用。',
 'Stabilizer':'双安瓿载架中分别封存两部分稳定成分，缓冲衬垫与固定夹保护细颈玻璃。用于缓释类药剂的配套材料，整组保存；不可直接饮用。',
 'Catalyst':'封存在观察罐中的活性晶簇，金属保护架与避光封盖维持完整封存状态。用于高浓度药剂的催化材料，应按完整密封单位保管。',
 'RedRoot':'从生态培育区赤脉根中保存的深红萃取物，琥珀滴瓶底部可见细小根纤维。作为生命恢复药剂的活性原料保管，未经调配不可直接服用。',
 'BlueFungus':'蓝髓菌培养物析出的蓝灰结晶，广口罐配有干燥包与密封防拆环。作为魔法恢复药剂的活性原料保存，整罐收集可减少受潮损耗。',
 'Silverleaf':'银叶花中封存的浅金精华，橄榄色瓶壁与保护套减少光照影响，瓶颈保留叶纹标记。作为清明类药剂的珍贵原料保存，不可直接饮用。'}
definitions={}
for key,a in spec['assets'].items():
 icon=next(i for i in icons['icons'] if i['id']==a['id']);mesh=next(i for i in meshes['meshes'] if i['item_id']==a['id'])
 definitions[a['id']]=dict(id=a['id'],name=a['name'],category='material',type='药剂材料',loot_group='alchemy',rarity=a['rarity'],price=a['value'],sell_souls=a['value'],desc=DESC[key],grid_w=a['grid'][0],grid_h=a['grid'][1],stack=a['stack'],stack_max=a['stack'],maxStack=a['stack'],inventory_unit='组' if key=='Stabilizer' else '份',icon=icon['ue_icon'],ue_icon=icon['ue_icon'],icon_fallback=a['name'],world_mesh=mesh['path'])
p=DATA/'items.json';raw=p.read_text('utf-8-sig');current=json.loads(raw)
prior_path=ROOT/'Receipts/data-installation.json'
prior=read(prior_path)['items'] if prior_path.exists() else {}
changed=False
for identity in definitions.keys()&current.keys():
 if current[identity]!=definitions[identity]:
  if current[identity]!=prior.get(identity):raise RuntimeError('Preserve changed existing item '+identity)
  old=json.dumps({identity:current[identity]},ensure_ascii=False,indent=2)[1:-1].strip('\n')
  new_fragment=json.dumps({identity:definitions[identity]},ensure_ascii=False,indent=2)[1:-1].strip('\n')
  if old not in raw:raise RuntimeError('Preserve concurrent item formatting '+identity)
  raw=raw.replace(old,new_fragment,1);changed=True
if changed:backup(p);p.write_text(raw,'utf8')
new={k:v for k,v in definitions.items() if k not in current}
if new:
 backup(p);tail=json.dumps(new,ensure_ascii=False,indent=2)[1:-1].strip('\n')
 p.write_text(raw[:raw.rfind('}')].rstrip()+',\n'+tail+'\n}\n','utf8')
B='alchemy_pure_base_fluid';S='alchemy_compound_stabilizer';C='alchemy_active_catalyst'
R='alchemy_redvein_extract';F='alchemy_bluemarrow_crystals';L='alchemy_silverleaf_essence'
def pool(identity,group,entries):
 return dict(id=identity,group=group,count_weights=[0,100,0,0],entries=[dict(id=k,weight=w) for k,w in entries])
pools=[
 pool('research_records','documents',[('search_usb_drive',90),('search_archive_tape',8),('search_certified_admin_archive',2)]),
 pool('medical_treatment_cart','medical',[('hp_potion',25),('hp_potion_medium',20),(B,25),(S,20),(C,5),(R,5)]),
 pool('medical_first_aid','medical',[('hp_potion',40),('hp_potion_medium',25),('hp_potion_high',10),(B,15),(S,10)]),
 pool('medical_reagent_stock','alchemy',[(B,45),(S,45),(C,10)]),
 pool('medical_sealed_samples','alchemy',[(B,25),(S,25),(R,15),(F,10),(C,15),(L,10)]),
 pool('medical_patient_supplies','daily_supplies',[('mineral_water',40),('bread',25),('soda_can',20),(B,10),(R,5)]),
 pool('research_maintenance','maintenance',[('search_assembly_component_box',32),('search_precision_mechanism',28),('search_industrial_multimeter',20),('search_power_control_module',10),('search_precision_tool_kit',8),('search_cordless_impact_wrench',2)]),
 pool('ecology_staff_supplies','daily_supplies',[('mineral_water',45),('bread',25),('soda_can',20),(B,10)]),
 pool('ecology_culture_stock','alchemy',[(B,30),(R,30),(F,20),(S,10),(C,5),(L,5)]),
 pool('ecology_botanical_archive','alchemy',[(R,45),(F,35),(B,10),(L,10)]),
 pool('ecology_sealed_samples','alchemy',[(R,30),(F,30),(B,15),(C,10),(L,15)]),
 pool('ecology_analysis_spares','alchemy',[(B,30),(S,30),('search_industrial_multimeter',30),(C,10)])]
def medical_pool(identity):
 if identity=='MedicalOffice.ClinicalFirstAid' or '.Ward.Emergency.' in identity:return 'medical_first_aid'
 if '.InstrumentCart' in identity or '.Ward.Cart.' in identity or identity in ('Hospital.Theatre.Cart','Hospital.Theatre.Gallery.West'):return 'medical_treatment_cart'
 if '.Theatre.Instruments.' in identity:return 'medical_reagent_stock'
 if identity in ('Hospital.Theatre.Specimens','Hospital.Theatre.Gallery.East'):return 'medical_sealed_samples'
 if identity=='Hospital.Theatre.Gallery.NorthWest':return 'medical_patient_supplies'
 if identity=='Hospital.Theatre.Gallery.NorthEast':return 'research_maintenance'
 if identity.startswith('MedicalOffice.') or identity.startswith('Hospital.Office.'):return 'research_records'
 raise RuntimeError('Unassigned medical container '+identity)
def ecology_pool(identity):
 if '.PPE' in identity:return 'ecology_staff_supplies'
 if '.Tote' in identity:return 'ecology_culture_stock'
 if '.Sample' in identity:return 'ecology_sealed_samples'
 if '.Seeds.' in identity:return 'ecology_botanical_archive'
 if '.Records' in identity:return 'research_records'
 if identity=='EcoHydroponics.Spare':return 'ecology_analysis_spares'
 if identity.startswith('EcoHydroponics.'):return 'research_maintenance'
 raise RuntimeError('Unassigned ecology container '+identity)
inventory=read(PROJECT/'Saved/DungeonRegionStatus20261014/regions.json');bindings=[]
for region in inventory['regions']:
 if region['region'] not in ('medical','ecology'):continue
 for room in region['rooms']:
  for entry in room['missing']:
   identity=entry['id'];profile=medical_pool(identity) if region['region']=='medical' else ecology_pool(identity)
   bindings.append(dict(container_id=identity,pool=profile,module=room['id'],caption=entry['caption']))
bindings.append(dict(container_id='Hospital.Bedside',pool='medical_patient_supplies',module='AbandonedIsolationWard',caption='病人物品箱',binding_scope='Generated ward bedside family; storage retains complete unique ContainerId'))
p=DATA/'scene_search_loot.json';loot=read(p);pool_ids={v['id'] for v in pools};ids={v['container_id'] for v in bindings}
for old in loot['pools']:
 if old['id'] in pool_ids and old not in pools:raise RuntimeError('Preserve changed pool '+old['id'])
for old in loot['bindings']:
 if old['container_id'] in ids and old not in bindings:raise RuntimeError('Preserve changed binding '+old['container_id'])
loot['pools']=[v for v in loot['pools'] if v['id'] not in pool_ids]+pools
loot['bindings']=[v for v in loot['bindings'] if v['container_id'] not in ids]+bindings;write(p,loot)
p=PROJECT/'Config/DefaultGame.ini';raw=p.read_text('utf-8-sig');entry='+DirectoriesToAlwaysCook=(Path="/Game/Items/AlchemyMaterials20261015/V3")'
old_entry='+DirectoriesToAlwaysCook=(Path="/Game/Items/AlchemyMaterials20261015/V2")'
if old_entry in raw:
 backup(p);raw=raw.replace(old_entry,entry);p.write_text(raw,'utf8')
if entry not in raw:
 backup(p);raw=raw.replace('[/Script/UnrealEd.ProjectPackagingSettings]','[/Script/UnrealEd.ProjectPackagingSettings]\n'+entry,1);p.write_text(raw,'utf8')
report=dict(stage='data_installed',timestamp_utc=datetime.now(timezone.utc).isoformat(),items=definitions,pools=pools,bindings=bindings,fixed_candidate_bindings=60,dynamic_family_bindings=1,crafting_implemented=False,tests_run=False,multiplayer_tested=False)
(ROOT/'Receipts/data-installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print('ALCHEMY_DATA_INSTALLED items=%d bindings=%d pools=%d'%(len(definitions),len(bindings),len(pools)))
