"""Publish saved assets/icons and bind only the incineration container identities."""
from pathlib import Path
from datetime import datetime,timezone
import json,shutil
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];DATA=PROJECT/'Content/ColdSteelData'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def backup(p):
    out=ROOT/'Before'/p.relative_to(PROJECT);out.parent.mkdir(parents=True,exist_ok=True)
    if not out.exists():shutil.copy2(p,out)
def save(p,value):
    backup(p);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if read(ROOT/'Receipts/installation.json')['stage']!='assets_installed':raise RuntimeError('Install UE packages first')
icons=read(ROOT/'presentation.json');meshes=read(ROOT/'Receipts/ue-import.json');spec=read(ROOT/'model_manifest.json')
if icons['stage']!='inventory_icons_saved':raise RuntimeError('Complete production icons first')
descriptions={
 'RespiratorFilter':'焚化区防护柜内封存的呼吸滤罐，压制金属壳、螺纹接头和运输封盖仍保持完整。作为防护备件收集物，可带回商店出售；当前不能直接装备。',
 'CeramicModule':'焚化炉检修库存中的耐火陶瓷组件，厚壁通道固定在金属托架内，边缘保留出厂批次标记。完整组件便于回收运输，可作为工业收集物出售。',
 'Thermocouple':'焚化区测温设备的备用热电偶，金属护套连接接线头与绝缘导线，外壳保留检修标签。可作为精密仪器收集物带回出售，不能直接用于测量或维修。',
 'IndustrialFilter':'烟气净化站封存的替换过滤芯，折叠滤材由金属端盖和支撑环固定，端部保留密封垫圈。可作为设备备件带回出售，体积较大，需要预留背包位置。',
 'IncidentArchive':'停尸档案柜内的封存事故卷宗，布面封皮下夹着焚化记录、交接页和设备异常报告，红色封条仍未拆开。可作为高价值文件带回出售。',
 'CatalyticCore':'烟气净化站的备用催化芯，蜂窝陶瓷通道装在带提手的不锈钢框架中，侧面铭牌记录着库存批次。可作为高价值工业收集物出售，搬运时需要较大的储物空间。'}
definitions={}
for key,row in spec['assets'].items():
    icon=next(x for x in icons['icons'] if x['id']==row['id'])
    mesh=next(x for x in meshes['meshes'] if x['item_id']==row['id'])
    target=DATA/icon['ue_icon'];target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if target.read_bytes()!=Path(icon['file']).read_bytes():raise RuntimeError('Preserve existing icon '+str(target))
    else:shutil.copy2(icon['file'],target)
    definitions[row['id']]=dict(id=row['id'],name=row['name'],category='material',
        type='文件收集物' if key=='IncidentArchive' else '焚化区收集物',
        loot_group='documents' if key=='IncidentArchive' else 'maintenance',rarity=row['rarity'],
        price=row['value'],sell_souls=row['value'],desc=descriptions[key],grid_w=row['grid'][0],grid_h=row['grid'][1],
        stack=1,stack_max=1,maxStack=1,inventory_unit='份' if key=='IncidentArchive' else '件',
        icon=icon['ue_icon'],ue_icon=icon['ue_icon'],icon_fallback=row['name'],world_mesh=mesh['path'])
p=DATA/'items.json';raw=p.read_text('utf-8-sig');current=json.loads(raw)
for identity in definitions.keys()&current.keys():
    if definitions[identity]!=current[identity]:raise RuntimeError('Preserve differing item '+identity)
new={k:v for k,v in definitions.items() if k not in current}
if new:
    backup(p);tail=json.dumps(new,ensure_ascii=False,indent=2)[1:-1].strip('\n')
    p.write_text(raw[:raw.rfind('}')].rstrip()+',\n'+tail+'\n}\n',encoding='utf-8')
def pool(name,group,entries):
    return dict(id=name,group=group,count_weights=[0,100,0,0],entries=[dict(id=k,weight=v) for k,v in entries])
pools=[
 pool('incineration_maintenance','maintenance',[
  ('search_precision_mechanism',25),('search_assembly_component_box',20),('search_forging_alloy_blank',20),
  ('search_high_temperature_thermocouple',15),('search_industrial_multimeter',12),('search_precision_tool_kit',6),('search_cordless_impact_wrench',2)]),
 pool('incineration_protection','maintenance',[
  ('search_sealed_respirator_filter',70),('search_high_temperature_thermocouple',10),('search_industrial_filter_cartridge',10),('search_precision_tool_kit',10)]),
 pool('incineration_heat','maintenance',[
  ('search_refractory_ceramic_module',45),('search_high_temperature_thermocouple',30),('search_forging_alloy_blank',15),('search_power_control_module',8),('search_flue_gas_catalytic_core',2)]),
 pool('incineration_records','documents',[
  ('search_usb_drive',65),('search_archive_tape',25),('search_sealed_incineration_archive',8),('search_certified_admin_archive',2)]),
 pool('incineration_filters','maintenance',[
  ('search_industrial_filter_cartridge',65),('search_sealed_respirator_filter',25),('search_flue_gas_catalytic_core',10)])]
family={'ToolBox':'incineration_maintenance','PPELocker':'incineration_protection','HeatCabinet':'incineration_heat','RecordsCabinet':'incineration_records','FilterCase':'incineration_filters'}
catalog=read(PROJECT/'SourceAssets/DungeonFacilityFlow20261007/Config/catalog.json');bindings=[]
def walk(node,module):
    if isinstance(node,dict):
        identity=node.get('container_id','')
        if identity.startswith('Treatment.'):
            bindings.append(dict(container_id=identity,pool=family[identity.split('.')[2]],module=module,caption=node['caption']))
        for v in node.values():walk(v,module)
    elif isinstance(node,list):
        for v in node:walk(v,module)
for module in catalog['modules']:
    if module['id'] in ('ShoredBreach','AbandonedIncineratorHall','AbandonedFlueGasStation'):walk(module.get('warehouse_containers',{}),module['id'])
p=DATA/'scene_search_loot.json';loot=read(p);pool_ids={x['id'] for x in pools};ids={x['container_id'] for x in bindings}
for old in loot['pools']:
    if old['id'] in pool_ids and old not in pools:raise RuntimeError('Preserve differing pool '+old['id'])
for old in loot['bindings']:
    if old['container_id'] in ids and old not in bindings:raise RuntimeError('Preserve differing binding '+old['container_id'])
loot['pools']=[x for x in loot['pools'] if x['id'] not in pool_ids]+pools
loot['bindings']=[x for x in loot['bindings'] if x['container_id'] not in ids]+bindings;save(p,loot)
p=PROJECT/'Config/DefaultGame.ini';raw=p.read_text('utf-8-sig');entry='+DirectoriesToAlwaysCook=(Path="/Game/Items/IncinerationCollectibles20261015/V1")'
if entry not in raw:
    backup(p);p.write_text(raw.replace('[/Script/UnrealEd.ProjectPackagingSettings]','[/Script/UnrealEd.ProjectPackagingSettings]\n'+entry,1),encoding='utf-8')
# rewards_deferred is authoring documentation, not a runtime reward switch.
p=PROJECT/'SourceAssets/IncineratorContainers20261003/Config/layout.json';layout=read(p)
layout['rewards_deferred']=False;layout['loot_config']='Content/ColdSteelData/scene_search_loot.json';save(p,layout)
report=dict(stage='data_installed',timestamp_utc=datetime.now(timezone.utc).isoformat(),items=definitions,pools=pools,bindings=bindings,
 fixed_candidate_bindings=len(bindings),search_entries_per_run=[22,25],physical_containers_per_run=[17,20],
 rarity_floor='rare',first_search_items=1,shared_server_inventory=True,crafting_implemented=False,tests_run=False,multiplayer_tested=False)
(ROOT/'Receipts/data-installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('INCINERATION_DATA_INSTALLED',len(definitions),len(bindings),len(pools))
