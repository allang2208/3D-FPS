"""Install new wood-core assets and narrow catalogue/loot additions."""
from pathlib import Path
import json,shutil
ROOT=Path(__file__).resolve().parents[2];TASK=ROOT/'SourceAssets/WoodCoreMaterials20261026';BEFORE=TASK/'Before'
cores=json.loads((TASK/'cores.json').read_text(encoding='utf-8'))
authored=json.loads((TASK/'ue-authoring.json').read_text(encoding='utf-8'))
if len(authored['saved_assets'])!=9:raise RuntimeError('UE asset authoring incomplete')
source=TASK/'AssetHost/Content/Items/WoodCores20261026';dest=ROOT/'Content/Items/WoodCores20261026'
if dest.exists():raise RuntimeError('Preserve existing destination; installation is one-time')
shutil.copytree(source,dest)
icons=ROOT/'Content/ColdSteelData/Icons/WoodCores20261026';icons.mkdir(parents=True,exist_ok=True)
for c in cores:shutil.copy2(TASK/'Icons'/f'{c["id"]}.png',icons/f'{c["id"]}.png')
def save(path,transform):
 p=ROOT/path;before=p.read_bytes();data=json.loads(before.decode('utf-8-sig'));transform(data)
 if p.read_bytes()!=before:raise RuntimeError('Concurrent edit: '+path)
 b=BEFORE/path;b.parent.mkdir(parents=True,exist_ok=True)
 if not b.exists():b.write_bytes(before)
 p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
descriptions=[
 '从干燥木料中截取并修整的实心木芯，去除树皮后保留清晰的纵向纤维与端面年轮。用作木工装备的主体选材，可由普通木材在工作台加工获得。',
 '工匠挑选深色心材制成的铁木芯，细密纤维沿长轴延伸，端面保留紧密环纹。作为木工装备的主体选材，提供稳定的材质基础，常见于维护物资与木工材料储备。',
 '从老树心部保留下来的古树木芯，深浅交错的生长纹理围绕结疤缓慢弯曲。经过干燥和截齐处理，可用于弓与法杖的木工制作，多从探索物资中取得。',
 '保留天然灵纹的实心木芯，灰绿色纤维间散布细弱的纹光。工匠只修整外缘与端面，留下内部纹理作为弓与法杖的制作主材，通常随珍贵探索奖励出现。']
new={}
for i,c in enumerate(cores):
 icon=f'Icons/WoodCores20261026/{c["id"]}.png'
 new[c['id']]=dict(id=c['id'],name=c['name'],category='material',type='木工材料',loot_group='maintenance',rarity=['common','uncommon','rare','epic'][i],price=[20,120,350,800][i],desc=descriptions[i],grid_w=2,grid_h=1,stack=1,stack_max=20,maxStack=20,inventory_unit='枚',icon=icon,ue_icon=icon,icon_fallback=c['name'],world_mesh=f'/Game/Items/WoodCores20261026/SM_WoodCore_{c["key"]}.SM_WoodCore_{c["key"]}')
# Append only new entries to the large shared catalogue; retain existing formatting and fields.
p=ROOT/'Content/ColdSteelData/items.json';before=p.read_bytes();raw=before.decode('utf-8-sig');catalog=json.loads(raw)
if any(k in catalog for k in new):raise RuntimeError('Core catalogue already present')
tail=raw.rfind('}');addition=json.dumps(new,ensure_ascii=False,indent=4)[1:-1].strip('\n')
result=raw[:tail].rstrip()+',\n'+addition+'\n'+raw[tail:]
if p.read_bytes()!=before:raise RuntimeError('Concurrent item catalogue edit')
b=BEFORE/'Content/ColdSteelData/items.json';b.parent.mkdir(parents=True,exist_ok=True);b.write_bytes(before);p.write_text(result,encoding='utf-8')
(ROOT/'Content/ColdSteelData/wood-cores.json').write_text(json.dumps({'version':1,'core_count':1,'cores':[dict(item=c['id'],name=c['name'],damage_bonus=c['bonus'],material=f'/Game/Items/WoodCores20261026/MI_WoodCore_{c["key"]}.MI_WoodCore_{c["key"]}') for c in cores]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def craft(d):d['recipes'].append(dict(id='craft_wood_core_plain',inputs=[dict(item='wood',count=2)],output=dict(item='wood_core_plain',count=1)))
save('Content/ColdSteelData/crafting-recipes.json',craft)
def recipe_comment(d):d['_comment']='木工专用长弓与长杖基础配方。新工件额外消耗 wood-cores.json 所选木芯 1 枚；统一报价与扣料由 WoodworkingSystem.InputsFor 处理。木芯保底 0/2/6/10%，加工评分提供 0～15%，最高合计25%。旧工件保持原工艺；免费工件不扣料不返料。'
save('Content/ColdSteelData/woodworking-recipes.json',recipe_comment)
def settings(d):d['_comment']='木工新工件记录木芯材质：保底0～10% + 加工0～15%；加工按完整度、边缘、清除率与用时评分，合格后领取。旧工件与成品保留原品质版本。弓仅修正物理伤害，法杖仅修正本件魔攻。'
save('Content/ColdSteelData/woodworking.json',settings)
def search(d):
 for pool in d['pools']:
  if pool['id'] in ('maintenance_parts','freight_maintenance','freight_tool_cabinet'):
   pool['entries']+= [dict(id='wood_core_iron',weight=8),dict(id='wood_core_ancient',weight=2)]
  elif pool['id']=='freight_tool_drawer':pool['entries'].append(dict(id='wood_core_iron',weight=5))
save('Content/ColdSteelData/scene_search_loot.json',search)
def dungeon(d):
 for tier in d['tiers']:
  if tier['min_depth']>=4:tier['entries'].append(dict(id='wood_core_ancient',weight=4,count=[1,1]))
  else:tier['entries'].append(dict(id='wood_core_iron',weight=5,count=[1,1]))
  if tier['min_depth']>=8:tier['entries'].append(dict(id='wood_core_spirit',weight=2,count=[1,1]))
 d['materials']['theme'].append(dict(id='wood_core_ancient',chance=.4,count=[1,1]))
 d['materials']['final'].append(dict(id='wood_core_spirit',chance=.6,count=[1,1]))
save('Content/ColdSteelData/dungeon_loot.json',dungeon)
(TASK/'installation.json').write_text(json.dumps(dict(installed_assets=authored['saved_assets'],installed_icons=[str(icons/f'{c["id"]}.png') for c in cores],acquisition='normal workbench + maintenance search pools + dungeon depth/theme/final reward',merchant='deferred: existing vendor sells food/water, no limited-stock contract',tree_assets='unchanged',gameplay_tests=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('Installed 9 saved UE assets, 4 icons, item catalogue, recipes and loot sources')
