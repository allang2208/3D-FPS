"""Stage the seven-family contract; publish exact catalog entries after asset authoring."""
from pathlib import Path
import json, copy, hashlib, sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/CampfireUpgrade20261026'
BASE='/Game/Items/Consumables/WildGame20261026'
ROWS=[
    dict(key='Venison',raw='raw_venison',cooked='roasted_venison',name='鹿肉',seconds=30,hunger=25,width=1.55,depth=.88,fat=.12,color=[.25,.038,.025]),
    dict(key='BoarMeat',raw='raw_boar_meat',cooked='roasted_boar_meat',name='野猪肉',seconds=40,hunger=30,width=1.9,depth=1.02,fat=.4,color=[.38,.085,.055]),
    dict(key='FoxMeat',raw='raw_fox_meat',cooked='roasted_fox_meat',name='狐肉',seconds=25,hunger=15,width=1.24,depth=.78,fat=.07,color=[.28,.055,.035])]
def asset(key,state):
    n=f'SM_{state}{key}';return f'{BASE}/{n}.{n}'
OUT.mkdir(parents=True,exist_ok=True)
if '--publish' not in sys.argv:
    (OUT/'foods.json').write_text(json.dumps(ROWS,ensure_ascii=False,indent=2),encoding='utf-8')
    host=OUT/'AssetHost';host.mkdir(exist_ok=True)
    (host/'AssetHost.uproject').write_text(json.dumps({'FileVersion':3,'EngineAssociation':'5.8','Description':'Isolated campfire food authoring','Plugins':[{'Name':'PythonScriptPlugin','Enabled':True},{'Name':'EditorScriptingUtilities','Enabled':True}]},indent=2),encoding='utf-8')
    print('Campfire food authoring staged');sys.exit()

def load(p):
    raw=p.read_bytes();return raw,json.loads(raw.decode('utf-8-sig'))
def save(p,before,value):
    if p.read_bytes()!=before:raise RuntimeError('Concurrent catalog edit: '+str(p))
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
items_path=ROOT/'Content/ColdSteelData/items.json';old,items=load(items_path)
recipes_path=ROOT/'Content/ColdSteelData/campfire-recipes.json';old_recipes,recipes=load(recipes_path)
for row in ROWS:
    for state in ('Raw','Roasted'):
        mesh_name=f'SM_{state}{row["key"]}'
        if not (ROOT/f'Content/Items/Consumables/WildGame20261026/{mesh_name}.uasset').is_file():raise RuntimeError('Author/import assets before publication')
        item_id=row['raw'] if state=='Raw' else row['cooked']
        if not (ROOT/f'Content/ColdSteelData/Icons/{item_id}.png').is_file():raise RuntimeError('Missing production icon '+item_id)
    raw=items[row['raw']];raw.pop('artPending',None)
    raw.update(desc=f'狩猎取得的生{row["name"]}，切成长条便于穿签烧烤。需要在篝火烤熟后食用，存放过久会腐败。',ue_icon=f'Icons/{row["raw"]}.png',world_mesh=asset(row['key'],'Raw'))
    cooked={k:copy.deepcopy(v) for k,v in raw.items() if k not in ('desc','artPending')}
    cooked.update(id=row['cooked'],name='烤'+row['name'],category='consumable',type='食物',spoilDays=4,
        desc=f'篝火烤熟的{row["name"]}，外层带有焦香色泽，切面保留肉的纤维纹理。可直接食用补充饱食度，及时领取并食用更为新鲜。',
        icon_fallback='烤'+row['name'],ue_icon=f'Icons/{row["cooked"]}.png',world_mesh=asset(row['key'],'Roasted'),maxUses=1,
        useEffect={'maxHungerPercent':row['hunger']},useDuration=2.4,useCooldown=0,
        stats=[{'name':'恢复饱食度','value':f'+{row["hunger"]}%上限'},{'name':'食用方式','value':'单次使用'}])
    items[row['cooked']]=cooked
    rid='roast_'+row['raw'].removeprefix('raw_')
    entry={'id':rid,'enabled':True,'input':{'item':row['raw'],'count':1},'output':{'item':row['cooked'],'count':1},'seconds':row['seconds'],
        'presentation':{'rawMesh':asset(row['key'],'Raw'),'cookedMesh':asset(row['key'],'Roasted'),'motionProfile':'roasted_sausage','spitAnchor':[0,-.16,.12]}}
    recipes['recipes']=[r for r in recipes['recipes'] if r['id']!=rid]+[entry]
for family,anchor in [('ChickenLeg',None),('LambRibs',[0,-.6,2.3]),('Sausage',None),('LargeLamb',[0,-4,2.7])]:
    cooked={'ChickenLeg':'roasted_chicken_leg','LambRibs':'roasted_lamb_ribs','Sausage':'roasted_sausage','LargeLamb':'roasted_large_lamb'}[family]
    for recipe in recipes['recipes']:
        if recipe['output']['item']!=cooked:continue
        p={'rawMesh':f'/Game/Items/Consumables/{family}20261014/Raw/SM_Raw{family}.SM_Raw{family}',
            'cookedMesh':f'/Game/Items/Consumables/{family}20261014/Roasted/SM_Roasted{family}.SM_Roasted{family}','motionProfile':cooked}
        if anchor:p['spitAnchor']=anchor
        recipe['presentation']=p
recipes['version']=2
save(items_path,old,items);save(recipes_path,old_recipes,recipes)
config=ROOT/'Config/DefaultGame.ini';text=config.read_text(encoding='utf-8-sig')
line='+DirectoriesToAlwaysCook=(Path="/Game/Items/Consumables/WildGame20261026")'
if line not in text:
    header='[/Script/UnrealEd.ProjectPackagingSettings]'
    if header not in text:raise RuntimeError('Packaging section missing')
    config.write_text(text.replace(header,header+'\n'+line,1),encoding='utf-8')
(OUT/'catalog-published.json').write_text(json.dumps({'families':[r['cooked'] for r in ROWS],'recipes':len(recipes['recipes']),
    'items_sha256':hashlib.sha256(items_path.read_bytes()).hexdigest(),'free_crafting':'ingredients only; paid wood'},indent=2),encoding='utf-8')
print('Campfire food catalog published')
