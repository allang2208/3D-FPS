"""One-time installation of the four approved material tiers; preserve existing items."""
from pathlib import Path
import json, shutil
ROOT=Path(__file__).resolve().parents[2];TASK=ROOT/'SourceAssets/CraftingMaterialTiers20261026';BEFORE=TASK/'Before'
ROWS=json.loads((TASK/'materials.json').read_text(encoding='utf-8'))
authored=json.loads((TASK/'ue-authoring.json').read_text(encoding='utf-8'))
if len(authored['saved_assets'])!=10:raise RuntimeError('Asset authoring has not completed')
BASE='/Game/Items/CraftingMaterialTiers20261026'

def backup(path,raw):
    p=BEFORE/path;p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():p.write_bytes(raw)
def save(path,change):
    p=ROOT/path;raw=p.read_bytes();data=json.loads(raw.decode('utf-8-sig'));change(data)
    out=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if p.read_bytes()!=raw:raise RuntimeError('Concurrent edit: '+path)
    backup(path,raw);p.write_bytes(out)

descriptions={
 'steelIngot':'以铁为基础精炼并调配的钢质铸锭，冷蓝灰表面保留细拉丝与单道压槽。可在高炉中精炼铁锭取得，也可从工业物资中回收；用于铁匠锻造和枪械装配的金属选材。',
 'platinumIngot':'银白色铂金铸锭，表面经过细磨，双道压槽用于辨识与堆放。铂具有耐腐蚀性，可从珍贵工业物资及深层探索奖励中取得，用于铁匠锻造和枪械装配的金属选材。',
 'wood_core_redgrain':'从赤褐心材中截取的实心木芯，交错红纹沿长轴展开，端面保留细密年轮。工匠将其干燥后修整成圆钝长坯，用作弓与法杖的主体材料，常见于木工物资和探索储备。',
 'wood_core_ebony':'经过干燥与修整的乌檀心材，深褐近黑的纤维间夹着细窄金棕纹，端面年轮清晰。表面保留自然哑光，无附加发光涂层，可从珍贵木工物资与深层探索奖励中取得，用作弓与法杖的主体材料。'
}
new={}
for c in ROWS:
    suffix=('Ingot_' if c['family']=='metal' else 'WoodCore_')+c['key'];icon=f'Icons/CraftingMaterialTiers20261026/{c["id"]}.png';stack=999 if c['family']=='metal' else 20
    new[c['id']]=dict(id=c['id'],name=c['name'],category='material',type='金属材料' if c['family']=='metal' else '木工材料',loot_group='maintenance',
        rarity=c['rarity'],price=c['price'],desc=descriptions[c['id']],grid_w=2,grid_h=1,stack=1,stack_max=stack,maxStack=stack,inventory_unit='块' if c['family']=='metal' else '枚',
        icon=icon,ue_icon=icon,icon_fallback=c['name'],world_mesh=f'{BASE}/SM_{suffix}.SM_{suffix}')

path='Content/ColdSteelData/items.json';p=ROOT/path;raw=p.read_bytes();text=raw.decode('utf-8-sig');current=json.loads(text)
if any(k in current for k in new):raise RuntimeError('New item IDs already exist; preserve current catalogue')
dest=ROOT/'Content/Items/CraftingMaterialTiers20261026'
if dest.exists():raise RuntimeError('New asset destination already exists; preserve saved packages')
shutil.copytree(TASK/'AssetHost/Content/Items/CraftingMaterialTiers20261026',dest)
icons=ROOT/'Content/ColdSteelData/Icons/CraftingMaterialTiers20261026';icons.mkdir(parents=True,exist_ok=True)
for c in ROWS:shutil.copy2(TASK/'Icons'/f'{c["id"]}.png',icons/f'{c["id"]}.png')
end=text.rfind('}');added=json.dumps(new,ensure_ascii=False,indent=4)[1:-1].strip('\n')
result=text[:end].rstrip()+',\n'+added+'\n'+text[end:]
if p.read_bytes()!=raw:raise RuntimeError('Concurrent items catalogue edit')
backup(path,raw);p.write_text(result,encoding='utf-8')

def metals(d):
    for c in ROWS:
        if c['family']=='metal':d['metals'].append(dict(item=c['id'],damage_bonus=c['bonus']))
    d['metals'].sort(key=lambda r:r['damage_bonus'])
    d['_comment']='锻造版本2：固定消耗合金胚、木材，另按 metal_count 消耗一种所选金属锭。铁0%、铜2%、钢4%、银6%、铂金8%、金10%；每次有效命中+0.75个百分点，20次最高+15%，总上限+25%。legacy_inputs仅用于缺少支付快照的旧档返料。枪械装配共用此金属目录。'
save('Content/ColdSteelData/forging-recipes.json',metals)
def cores(d):
    for c in ROWS:
        if c['family']=='wood':d['cores'].append(dict(item=c['id'],name=c['name'],damage_bonus=c['bonus'],material=f'{BASE}/MI_WoodCore_{c["key"]}.MI_WoodCore_{c["key"]}'))
    d['cores'].sort(key=lambda r:r['damage_bonus'])
save('Content/ColdSteelData/wood-cores.json',cores)
def wood_comment(d):
    d['_comment']='木工固定配方加所选木芯1枚；原木0%、铁木2%、赤纹4%、古树6%、乌檀8%、灵纹10%。加工评分另计0～15%，总上限25%。InputsFor统一报价与扣料；旧工件保持原工艺，免费工件不扣料不返料。'
save('Content/ColdSteelData/woodworking-recipes.json',wood_comment)
def smelting(d):
    d['recipes'].append(dict(id='refine_steel',input=dict(item='ironIngot',count=2),output=dict(item='steelIngot',count=1),seconds=16.0))
    d['_comment']+=' 钢锭精炼：2铁锭→1钢锭，基础16秒，沿用现有炉火燃料、加速与批量规则；铂金本轮通过探索获取。'
save('Content/ColdSteelData/smelting-recipes.json',smelting)
def search(d):
    for pool in d['pools']:
        key=pool['id']
        if key in ('maintenance_parts','freight_maintenance','freight_tool_cabinet'):
            pool['entries'] += [dict(id='steelIngot',weight=5),dict(id='wood_core_redgrain',weight=4)]
        elif key=='freight_tool_drawer':pool['entries'].append(dict(id='wood_core_redgrain',weight=3))
        if key in ('power_maintenance','research_maintenance','freight_hardware'):pool['entries'].append(dict(id='platinumIngot',weight=2))
        if key in ('freight_tool_cabinet','ecology_sealed_samples'):pool['entries'].append(dict(id='wood_core_ebony',weight=1))
save('Content/ColdSteelData/scene_search_loot.json',search)
def dungeon(d):
    for tier in d['tiers']:
        if tier['min_depth']>=4:
            tier['entries'] += [dict(id='steelIngot',weight=6,count=[2,6]),dict(id='wood_core_redgrain',weight=4,count=[1,1])]
        if tier['min_depth']>=8:
            tier['entries'] += [dict(id='platinumIngot',weight=3,count=[2,5]),dict(id='wood_core_ebony',weight=3,count=[1,1])]
    d['materials']['theme'] += [dict(id='wood_core_redgrain',chance=.45,count=[1,1]),dict(id='wood_core_ebony',chance=.25,count=[1,1])]
    d['materials']['final'] += [dict(id='platinumIngot',chance=.4,count=[2,4]),dict(id='wood_core_ebony',chance=.35,count=[1,1])]
save('Content/ColdSteelData/dungeon_loot.json',dungeon)

path='Config/DefaultGame.ini';p=ROOT/path;raw=p.read_bytes();text=raw.decode('utf-8-sig');entry=f'+DirectoriesToAlwaysCook=(Path="{BASE}")'
if entry not in text:
    section='[/Script/UnrealEd.ProjectPackagingSettings]'
    if section not in text:raise RuntimeError('Packaging settings section not found')
    updated=text.replace(section,section+'\n'+entry,1)
    if p.read_bytes()!=raw:raise RuntimeError('Concurrent packaging settings edit')
    backup(path,raw);p.write_text(updated,encoding='utf-8')
(TASK/'installation.json').write_text(json.dumps(dict(installed_assets=authored['saved_assets'],items=list(new),icons=[str(icons/f'{c["id"]}.png') for c in ROWS],
    metal_consumers=['forging','gun assembly'],wood_consumers=['woodworking'],floors=[0,.02,.04,.06,.08,.10],
    acquisition='steel furnace refining; search pools; dungeon depth/theme/final rewards',gameplay_test=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('Installed 10 UE packages, four icons and six-tier workbench catalogues')
