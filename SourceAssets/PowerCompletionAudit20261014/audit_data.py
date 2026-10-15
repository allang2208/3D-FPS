"""Check the delivered item/catalog/cook contract against the saved-map readback."""
from pathlib import Path
import json
from PIL import Image

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
read=lambda p:json.loads(p.read_text('utf-8-sig'))
items=read(PROJECT/'Content/ColdSteelData/items.json')
loot=read(PROJECT/'Content/ColdSteelData/scene_search_loot.json')
saved=read(ROOT/'assets.json')
checks=[]
def require(ok,label,detail=None):checks.append(dict(pass_=bool(ok),label=label,detail=detail))
cfg=(PROJECT/'Config/DefaultGame.ini').read_text('utf-8-sig')
require('/Game/Items/PowerCollectibles20261014/V1' in cfg,'new item packages explicitly cooked')
build_rules=(PROJECT/'Source/FPSGAME/FPSGAME.Build.cs').read_text('utf-8-sig')
require('DirectoriesToAlwaysStageAsUFS=(Path="ColdSteelData")' in cfg
    or 'RuntimeDependencies.Add("$(ProjectDir)/Content/ColdSteelData/...", StagedFileType.UFS)' in build_rules,
    'item data and PNG icons staged')
for name in ['FacelessResearcher','CargoTechnician','VortexCofferM25','HangingBellM09/V10']:
    require('/Game/Monsters/'+name in cfg,name+' runtime monster assets cooked')
expected={'search_industrial_fuse_set':(1,1,120),'search_power_control_module':(2,1,900),'search_energy_storage_cell':(1,2,1600)}
native=(PROJECT/'Source/FPSGAME/UI/ColdSteelPickupConsumable.cpp').read_text('utf-8-sig')
for identity,(w,h,value) in expected.items():
    item=items[identity]
    require((item['grid_w'],item['grid_h'],item['sell_souls'])==(w,h,value),identity+' grid and sale value')
    require(identity in native,identity+' authored ground pickup branch')
    with Image.open(PROJECT/'Content/ColdSteelData'/item['ue_icon']) as icon:
        require(icon.mode=='RGBA' and icon.size==(512*w,512*h),identity+' RGBA inventory icon dimensions')
        bounds=icon.getchannel('A').getbbox()
        require(bounds is not None and bounds[0]>0 and bounds[1]>0 and bounds[2]<icon.width and bounds[3]<icon.height,identity+' complete silhouette and transparent margin',bounds)
toolboxes=[r['recipe'] for r in saved['containers'] if '.MaintenanceToolbox.' in r['id']]
for source in ['SourceAssets/DungeonPowerTheme20261004RefineV2/Config/module-drafts.json','SourceAssets/DungeonFacilityFlow20261007/Config/catalog.json']:
    module=next(m for m in read(PROJECT/source)['modules'] if m['id']=='GeneratorHall')
    for recipe in toolboxes:
        actor=next((a for a in module['runtime_actors'] if a.get('container_id')==recipe['container_id']),None)
        require(actor is not None and all(actor.get(k)==recipe.get(k) for k in ['position','yaw','body','door','hinge','opening_motion','opened_roll','storage_pages']),source+' '+recipe['container_id']+' matches saved map')
power_ids={row['id'] for row in saved['containers']}
bound=[row for row in loot['bindings'] if row['container_id'] in power_ids]
require(len(bound)==14,'all power searchable containers bound once')
for row in bound:
    if '.Server.' in row['container_id']: require(row['pool']=='server_hardware',row['container_id']+' existing server pool preserved')
    else:
        pool=next(p for p in loot['pools'] if p['id']==row['pool'])
        require(pool['count_weights']==[0,100,0,0],row['container_id']+' one initial item')
report=dict(checks=checks,failures=[r for r in checks if not r['pass_']],player_saves_modified=False)
(ROOT/'data.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('POWER_DATA_AUDIT checks=%d failures=%d'%(len(checks),len(report['failures'])))
if report['failures']:print(json.dumps(report['failures'],ensure_ascii=False));raise SystemExit(1)
