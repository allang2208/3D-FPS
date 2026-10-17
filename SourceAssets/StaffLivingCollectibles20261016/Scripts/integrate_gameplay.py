"""Register the approved footprints and bind only the 67 staff living search entries."""
from pathlib import Path
from datetime import datetime,timezone
import json,shutil,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];DATA=PROJECT/'Content/ColdSteelData'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def backup(p):
 q=ROOT/'Before/GameplayIntegration20261016'/p.relative_to(PROJECT);q.parent.mkdir(parents=True,exist_ok=True)
 if p.exists() and not q.exists():shutil.copy2(p,q)
def write_json(p,obj):
 backup(p);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
camera=read(ROOT/'Receipts/camera-text-v2-import.json')
if camera['stage']!='camera_v2_saved':raise RuntimeError('Finish corrected camera asset save first')
staged=ROOT/'UEImportHost/Content/Items/StaffLivingCollectibles20261016/V2'
installed=[]
for p in sorted(staged.rglob('*')):
 if p.suffix not in ('.uasset','.ubulk','.uexp'):continue
 target=PROJECT/'Content/Items/StaffLivingCollectibles20261016/V2'/p.relative_to(staged)
 if target.exists() and target.read_bytes()!=p.read_bytes():raise RuntimeError('Preserve different camera revision '+str(target))
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target);installed.append(str(target))
icon=ROOT/'Icons/search_compact_camera.png';target=DATA/'Icons/StaffLivingCollectibles20261016/search_compact_camera.png';backup(target);shutil.copy2(icon,target)
definitions=read(ROOT/'item_definitions.proposed.json')
definitions['search_compact_camera']['world_mesh']=camera['path']
for item in definitions.values():item['loot_region']='staff_living'
p=DATA/'items.json';raw=p.read_text('utf-8-sig');current=json.loads(raw)
for identity in current.keys()&definitions.keys():
 if current[identity]!=definitions[identity]:raise RuntimeError('Preserve an independently modified item '+identity)
fresh={k:v for k,v in definitions.items() if k not in current}
if fresh:
 backup(p);tail=json.dumps(fresh,ensure_ascii=False,indent=2)[1:-1].strip('\n')
 p.write_text(raw[:raw.rfind('}')].rstrip()+',\n'+tail+'\n}\n',encoding='utf-8')
def pool(name,group,weights):
 return dict(id=name,group=group,count_weights=[0,100,0,0],entries=[dict(id=k,weight=v) for k,v in weights])
pools=[
 pool('staff_personal_locker','daily_supplies',[
  ('mineral_water',30),('soda_can',20),('bread',18),('baguette_bread',8),('search_usb_drive',12),
  ('search_private_perfume',7),('search_portable_music_player',3),('search_compact_camera',1),('search_business_laptop',1)]),
 pool('staff_changing_personal','daily_supplies',[
  ('mineral_water',40),('soda_can',24),('bread',14),('search_usb_drive',12),
  ('search_private_perfume',7),('search_portable_music_player',2),('search_compact_camera',1)]),
 pool('staff_bedside','daily_supplies',[
  ('mineral_water',26),('soda_can',18),('bread',18),('search_usb_drive',20),
  ('search_private_perfume',10),('search_portable_music_player',5),('search_compact_camera',2),('search_business_laptop',1)]),
 pool('staff_documents','documents',[
  ('search_usb_drive',66),('search_archive_tape',24),('search_certified_admin_archive',8),('search_encrypted_archive_case',2)]),
 pool('staff_personal_electronics','daily_supplies',[
  ('search_usb_drive',65),('search_hard_disk',15),('search_ssd',8),('search_archive_tape',7),
  ('search_portable_music_player',3),('search_compact_camera',1),('search_business_laptop',1)]),
 pool('staff_pantry','daily_supplies',[
  ('mineral_water',35),('soda_can',30),('bread',25),('baguette_bread',10)]),
 pool('staff_refrigerated','daily_supplies',[
  ('mineral_water',40),('soda_can',30),('raw_sausage',20),('raw_chicken_leg',10)]),
 pool('staff_frozen','daily_supplies',[
  ('raw_sausage',35),('raw_chicken_leg',35),('raw_lamb_ribs',25),('raw_large_lamb',5)])]
catalog=read(PROJECT/'SourceAssets/DungeonFacilityFlow20261007/Config/catalog.json');bindings=[]
for module in catalog['modules']:
 if module['id'] not in ('StaffDormitory','StaffChangingShowers','StaffRecreation'):continue
 for spec in module['scene_containers']:
  identity=spec['container_id'];part=identity.split('.',1)[1]
  if module['id']=='StaffChangingShowers':profile='staff_changing_personal';caption='员工更衣柜'
  elif part.startswith('Locker_'):profile='staff_personal_locker';caption='员工衣柜'
  elif part.startswith('Bedside'):profile='staff_bedside';caption='床头柜'
  elif part.startswith('Bookcase_'):profile='staff_documents';caption='员工书柜'
  elif part.startswith('Bookshelf_'):profile='staff_personal_electronics';caption='员工书架'
  elif part.startswith('CounterCabinet_'):profile='staff_pantry';caption='茶水台储物柜'
  elif part=='FridgeLower':profile='staff_refrigerated';caption='冰箱冷藏室'
  elif part=='FridgeUpper':profile='staff_frozen';caption='冰箱冷冻室'
  else:raise RuntimeError('Container needs an explicit authored pool: '+identity)
  bindings.append(dict(container_id=identity,pool=profile,module=module['id'],caption=spec.get('caption',caption)))
p=DATA/'scene_search_loot.json';loot=read(p);newp={x['id']:x for x in pools};newb={x['container_id']:x for x in bindings}
for old in loot['pools']:
 if old['id'] in newp and old!=newp[old['id']]:raise RuntimeError('Preserve an independently modified pool '+old['id'])
for old in loot['bindings']:
 if old['container_id'] in newb and old!=newb[old['container_id']]:raise RuntimeError('Preserve an independently modified binding '+old['container_id'])
loot['pools']=[x for x in loot['pools'] if x['id'] not in newp]+pools
loot['bindings']=[x for x in loot['bindings'] if x['container_id'] not in newb]+bindings;write_json(p,loot)
p=PROJECT/'Config/DefaultGame.ini';raw=p.read_text('utf-8-sig');add=[]
for version in ('V1','V2'):
 entry='+DirectoriesToAlwaysCook=(Path="/Game/Items/StaffLivingCollectibles20261016/'+version+'")'
 if entry not in raw:add.append(entry)
if add:
 backup(p);raw=raw.replace('[/Script/UnrealEd.ProjectPackagingSettings]','[/Script/UnrealEd.ProjectPackagingSettings]\n'+'\n'.join(add),1);p.write_text(raw,encoding='utf-8')
write_json(ROOT/'item_definitions.json',definitions)
counts={pool['id']:sum(b['pool']==pool['id'] for b in bindings) for pool in pools}
report=dict(stage='gameplay_data_installed',completed_utc=datetime.now(timezone.utc).isoformat(),
 items=definitions,pools=pools,bindings=bindings,container_counts=counts,first_search_items=1,
 scope='Staff living only; excludes equipment, existing treasure chests and other regions',
 updated_camera_assets=installed,table_totals={'pools':len(loot['pools']),'bindings':len(loot['bindings']),'distinct_items':len({e['id'] for pool in loot['pools'] for e in pool['entries']})},
 shared_server_inventory='Existing ColdSteelSceneLoot/SharedContainers transactions retained',
 tests_run=False,game_run=False)
write_json(ROOT/'Receipts/gameplay-data-installation.json',report)
write_json(ROOT/'loot_plan.active.json',{'stage':'installed','equipment_allowed':False,'pools':pools,'bindings':bindings,'first_search_items':1})
lines=['生活区收集品与搜索池正式接入','',
 '四件物品均为非装备收集物。占格按用户确认：香水 1×2、音乐播放器 1×2、相机 2×2、笔记本电脑 3×2。','相机背面按键文字已调整为正向，V2 网格复用 V1 材质；原 V1 网格保留。',
 '67 个生活区入口分配到 8 个池；首次生成固定 1 件。下列权重总和均为 100，亦为每次首次搜索的出现百分比。','不重置已生成、取空或保存的搜索结果；运行种子和完整容器 ID、共享库存事务沿用原实现。','']
names={**read(DATA/'items.json')}
for row in pools:
 lines.append(row['id']+'（'+str(counts[row['id']])+' 个入口）')
 lines.append('；'.join(names[e['id']]['name']+' '+str(e['weight'])+'%' for e in row['entries']));lines.append('')
lines.extend(['回收价沿用本批物品方案：香水 900、音乐播放器 1200、相机 2400、笔记本电脑 3600 灵魂；新物品每格占用、图标与模型身份对应。','所有食品沿用既有烹饪、生存与腐败定义，不添加新食用效果。','未向生活区池投放衣物、鞋、手套、背包、武器或其他装备。','本次范围不包含生活区首领、刷怪或区域闸门；排水过渡房与医疗宝箱也未改动。','',
 '已写入：items.json、scene_search_loot.json、DefaultGame.ini；拾取源码接入四件模型。','必要构建记录：Receipts/native-integration-build.json；此数据安装记录不代替构建结果。','未运行游戏、自动化、截图或主客机测试。新进程读取更新的搜索表；此前已经生成的容器内容保留。'])
(ROOT/'GAMEPLAY-INTEGRATION.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'stage':report['stage'],'new_items':len(definitions),'new_pools':len(pools),'bound_containers':len(bindings),'counts':counts,'table_totals':report['table_totals']},ensure_ascii=False))
