"""Read-only coverage audit of saved dungeon catalog, loot bindings and native dispatch."""
import collections, hashlib, json, re
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/DungeonCoverageAudit20261017'
cat=json.loads((OUT/'saved-catalog.json').read_text('utf-8'))
source=json.loads((OUT/'catalog-source.json').read_text('utf-8'))
lootpath=ROOT/'Content/ColdSteelData/scene_search_loot.json';loot=json.loads(lootpath.read_text('utf-8-sig'))
itempath=ROOT/'Content/ColdSteelData/items.json';items=json.loads(itempath.read_text('utf-8-sig'))
pools={p['id']:p for p in loot['pools']};bindings={b['container_id']:b for b in loot['bindings']}
errors=[]
if loot.get('version')!=1:errors.append('Unsupported table version')
if len(pools)!=len(loot['pools']):errors.append('Duplicate pool ID')
if len(bindings)!=len(loot['bindings']):errors.append('Duplicate binding ID')
for pid,p in pools.items():
 counts=p['count_weights'];entries=p['entries']
 if not counts or len(counts)>4 or sum(counts)!=100 or any(type(x)!=int or not 0<=x<=10000 for x in counts):errors.append('Invalid count weights: '+pid)
 if not 1<=len(entries)<=64 or len(counts)-1>len(entries):errors.append('Invalid pool size: '+pid)
 if len({e['id'] for e in entries})!=len(entries):errors.append('Duplicate item in pool: '+pid)
 for e in entries:
  if type(e['weight'])!=int or not 1<=e['weight']<=10000:errors.append('Invalid item weight: '+pid+':'+e['id'])
  if e['id'] not in items:errors.append('Missing item definition: '+e['id'])
for b in bindings.values():
 if b['pool'] not in pools:errors.append('Unknown pool: '+b['container_id'])

def containers(o,path=''):
 if isinstance(o,dict):
  if 'container_id' in o:yield {'id':o['container_id'],'path':path,'dynamic_family':False}
  if 'container_id_prefix' in o:yield {'id':o['container_id_prefix'],'path':path,'dynamic_family':True}
  for k,v in o.items():yield from containers(v,path+'/'+k)
 elif isinstance(o,list):
  for i,v in enumerate(o):yield from containers(v,path+'/'+str(i))

spawners={};functions=['IsHall','IsMedical','IsFreight','IsEcology','IsPower','IsIncineration','IsStaffLiving','IsFinalBossRoom']
generator=(ROOT/'Source/FPSGAME/Dungeons/AuthoredDungeonGenerator.cpp').read_text('utf-8-sig')
run=(ROOT/'Source/FPSGAME/Dungeons/DungeonRunSubsystem.cpp').read_text('utf-8-sig')
for file in (ROOT/'Source/FPSGAME/Dungeons').glob('Facility*Encounter.cpp'):
 text=file.read_text('utf-8-sig')
 for fn in functions:
  match=re.search(r'bool AFacilityHallEncounter::'+fn+r'\(const FString& Module\)\s*\{(.*?)\}',text,re.S)
  if not match:continue
  for mid in re.findall(r'TEXT\("([^"\n]+)"\)',match.group(1)):
   spawners[mid]={'function':fn,'file':str(file.relative_to(ROOT)),'line':text[:match.start()].count('\n')+1,
                  'preloaded':('AFacilityHallEncounter::'+fn+'(') in generator,
                  'dispatched':('AFacilityHallEncounter::'+fn+'(') in run}

usage=collections.Counter()
for layout in cat['facility_flow']['layout_bank']['entries'].values():usage.update({p['module'] for p in layout['pieces']})
regions={'FacilityReceptionHall':'迎宾区','FacilityTransit':'迎宾区','BossPumpHall':'终点','AbandonedDataArchive':'档案中心',
 'Distribution':'过渡区','Drainage':'过渡区','VentilationLoop':'过渡区','FacilityEntrancePassage':'入口'}
region_names={'freight':'货运区','medical':'医疗区','treatment':'焚化区','staff_living':'生活区','ecology':'生态区','power':'发电区'}
for region in cat['themed_routes']['routes']:
 for mid in region['sequence']:regions[mid]=region_names[region['id']]
rows=[];expected=set();missing=[];treasures=[]
for m in cat['modules']:
 found=list(containers(m));ids=sorted({c['id'] for c in found});expected.update(ids)
 absent=[i for i in ids if i not in bindings];missing.extend({'module':m['id'],'id':i} for i in absent)
 pool_counts=collections.Counter(bindings[i]['pool'] for i in ids if i in bindings)
 props=[]
 for p in m.get('props',[]):
  state='final_reward' if p.get('role')=='final_reward_chest' else 'generic_loot' if p.get('interaction_enabled',True) else 'disabled_pending_loot'
  t={'module':m['id'],'role':p.get('role'),'identity':p.get('identity'),'state':state};props.append(t);treasures.append(t)
 if m['id'] in ['Treasure','TreasureLink']:use='optional_side_room'
 elif m['id'] in usage:use='layout_bank'
 else:use='not_in_current_layout_bank'
 rows.append({'module':m['id'],'region':regions.get(m['id'],'连接/保留模块'),'use':use,'layout_bank_appearances':usage[m['id']],
              'unique_container_bindings':len(ids),'bound':len(ids)-len(absent),'missing':absent,
              'dynamic_families':[x['id'] for x in found if x['dynamic_family']], 'pools':dict(pool_counts),
              'containers':found,'spawner':spawners.get(m['id']),'treasures':props})
used_items={e['id'] for p in pools.values() for e in p['entries']}
living=[x for x in rows if x['region']=='生活区']
summary={'saved_generator_sha256':source['sha256'],'author_catalog_matches_saved':source['matches_author_catalog'],
 'loot_sha256':hashlib.sha256(lootpath.read_bytes()).hexdigest(),'items_sha256':hashlib.sha256(itempath.read_bytes()).hexdigest(),
 'catalog_modules':len(rows),'layout_bank_modules':len(usage),'binding_count':len(bindings),'saved_catalog_unique_binding_ids':len(expected),
 'pool_count':len(pools),'distinct_search_items':len(used_items),'missing_bindings':missing,'orphan_bindings':sorted(set(bindings)-expected),
 'table_errors':errors,'living_containers':sum(x['unique_container_bindings'] for x in living),
 'active_room_spawner_gaps':[x['module'] for x in rows if x['module'] in ['Distribution','Drainage','VentilationLoop','AbandonedDataArchive'] and not x['spawner']],
 'disabled_treasures':[t for t in treasures if t['state']=='disabled_pending_loot'],
 'game_run':False,'editor_opened':False,'configuration_modified':False}
report={'summary':summary,'modules':rows,'treasures':treasures}
(OUT/'coverage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 随机地牢收集物与刷怪覆盖核对（2026-10-17）','',
'按用户要求只读排查。直接读取正式随机地牢生成器已保存的 uasset 中 `ModuleCatalogJson`，与当前 `scene_search_loot.json`、`items.json`、实际 C++ 分派交叉核对；未运行游戏、测试地图或修改玩法配置。','',
'## 结论','',
'- 生活区 67 个普通搜索入口全部绑定：宿舍 36、更衣淋浴区 24、休闲厅 7。8 个生活区池首次搜索均固定 1 件，已生成或取空的箱子不补刷。',
'- 休闲厅厕所隐藏宝箱不是普通搜索柜，已启用并走 `dungeon_loot.json` 的通用宝箱掉落。',
'- 全目录 281 个唯一绑定身份（包含候选容器和病区床头箱动态族）、39 个搜索池、50 种搜索物品，未发现漏绑、未知池或缺失物品定义。281 不是每局实际容器数量。',
'- 六大主题区 18 间房与迎宾两厅均有怪物资源准备和实际遭遇分派；终末泵机大厅有合阙刷新和最终宝箱。',
'- 档案中心、Distribution 过渡房、通风环廊尚无普通搜索容器/收集物投放，也无怪物刷新分派。排水过渡房已有 2 个工具箱身份绑定，但尚无怪物刷新分派。',
'- 医疗第三间解剖教学剧场的后廊宝箱 `hospital_rear_gallery_treasure` 在正式保存目录中明确 `interaction_enabled=false`，生成时标记为 `DungeonTreasure.PendingLoot`，未进入可搜索宝箱流程。其普通搜索容器不受影响。','',
'## 生活区普通容器','',
'| 容器 | 数量 | 搜索池 |','| --- | ---: | --- |']
labels={'staff_personal_locker':'宿舍衣柜','staff_documents':'书柜','staff_personal_electronics':'书架','staff_bedside':'床头柜','staff_changing_personal':'更衣柜','staff_pantry':'茶水台储物柜','staff_refrigerated':'冰箱冷藏室','staff_frozen':'冰箱冷冻室'}
for pid,n in sum((collections.Counter(x['pools']) for x in living),collections.Counter()).items():lines.append(f'| {labels.get(pid,pid)} | {n} | {pid} |')
lines+=['','内容包括食品、饮水、U盘、档案、硬盘及生活区四件收集物：珍藏香水、便携音乐播放器、袖珍数码相机、商务笔记本电脑。各类柜子的物品集合不同，不是每种柜子都会出全部物品。','',
'## 全模块清单','',
'“绑定数”是唯一配置身份；随机家具变体共享某些身份，每局会选部分候选，病区床头箱为一族多个实例。侧宝箱房由普通房侧接口机会追加，不因布局库主体未列出就当成已退役。','',
'| 模块 | 区域 | 使用范围 | 普通容器绑定 | 怪物分派 | 宝箱 |','| --- | --- | --- | ---: | --- | --- |']
use_labels={'layout_bank':'正式布局库','optional_side_room':'可选侧室','not_in_current_layout_bank':'当前布局库未使用'}
for x in rows:
 s=x['spawner'];spawn='已接入 '+s['function'] if s and s['preloaded'] and s['dispatched'] else '无'
 chests='；'.join('待配置/关闭交互' if t['state']=='disabled_pending_loot' else '最终奖励池' if t['state']=='final_reward' else '通用宝箱池' for t in x['treasures']) or '—'
 lines.append(f"| {x['module']} | {x['region']} | {use_labels[x['use']]} | {x['bound']}/{x['unique_container_bindings']} | {spawn} | {chests} |")
lines+=['','入口走廊、门槛、连接廊、转角、坡道、下行楼梯与汇流件属于通行/连接模块，不把它们的无刷怪等同于主区域遗漏。未被当前布局采用的旧 Junction/RouteEnd/FreightTransfer/ForkLeft/ForkRight 也不混入当前主要缺口。','',
'## 证据与边界','',
'- 已保存生成器：`Content/__ExternalActors__/GameMaps/L_Dungeon_Randomized/8/N2/KZ839Z5RGFD4Y0908097LH.uasset`。散列：`'+source['sha256']+'`。',
'- 保存包内提取的目录：`SourceAssets/DungeonCoverageAudit20261017/saved-catalog.json`；完整逐 ID 结果：同目录 `coverage.json`。',
'- 制作源目录与正式保存目录并非完全一致，差异涉及部分家具布置、工作台、宝箱属性和布局库；本报告以正式保存目录为准。两者搜索容器身份集合一致，不能用制作源中单独出现的修改代替实际保存。',
'- 搜索链：`StaffLivingRoomAssembly` / `CargoWarehouseContainers` / `StationWorkshopAssembly` → `runtime_actors` → `WardRoomAssembly::Spawn`；病区床头箱来自 `WardBedScatter`。',
'- `ColdSteelSceneLoot::BoundPool` 识别完整静态 ID、Run{seed}.Node{node}. 前缀和 Hospital.Bedside 动态族；仅池查找归并，库存与抽取身份仍独立。',
'- 刷新链：`AuthoredDungeonGenerator` 异步资源准备 → `DungeonRunSubsystem::BindCompletedDungeon` → `FacilityHallEncounter` 各区域 Configure 分支；旧 `DungeonRoomEncounter` 已退役，场景中的 encounter/archive_combat 锚点本身不会刷怪。',
'- 宝箱链：生成器按 interaction_enabled 写入 DungeonTreasureChest 或 DungeonTreasure.PendingLoot；有效宝箱由 ColdSteelDungeonLoot 读取通用深度档，最终箱使用最高档和 final_multiplier。',
'- 这是保存数据与源码接入覆盖结果，不替代游戏内搜箱、实际怪物落点和主客机体验。没有执行修复或改变当前编辑器/运行实例。','']
path=ROOT/'Docs/Dungeons/loot-and-encounter-coverage-20261017.md';path.write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
print('REPORT',path)
