"""Publish server collectible definitions and their authored inventory images."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
ICONS=json.loads((ROOT/'inventory_icons.json').read_text('utf-8'))
if ICONS['stage']!='icons_saved':raise RuntimeError('Finish icon production before catalog publication')
MESHES={m['item_id']:m for m in json.loads((ROOT/'Receipts/ue-import.json').read_text('utf-8'))['meshes']}
DESIGN_PATH=PROJECT/'Docs/Gameplay/search-item-catalog-v2-20261012.json'
DESIGN=json.loads(DESIGN_PATH.read_text('utf-8'))
ITEMS={item['id']:item for item in DESIGN['items']}
DESC={
 'search_ram_module':'从设施服务器拆出的内存模块，双面存储颗粒、金手指与资产标签保留完整。它承载设备运行所需的临时数据，是机房中便于携带的回收硬件。',
 'search_network_card':'设施服务器使用的双口网络扩展卡，金属挡板保护着屏蔽接口，控制芯片配有独立散热片。接口与板材完整的模块具有回收价值。',
 'search_hard_disk':'设施机房保存资料的机械硬盘，厚实底壳、金属顶盖与资产标签仍然完整。它以磁性盘片保存数据，是值得带回的存储硬件。',
 'search_ssd':'设施计算设备拆出的固态存储器，薄金属壳保护着闪存和控制电路。外壳与接口完整，适合作为高价值硬件收集品带回。',
 'search_processor':'设施服务器的处理器模块，金属顶盖与封装基板保留在防静电保护托中。接触面受到保护，完整封装使其具有较高回收价值。',
 'search_graphics_card':'设施计算中心使用的图形扩展卡，双风扇、散热鳍片与辅助供电接口组成完整模块。体积较大，但板卡与散热结构齐全，具有较高回收价值。',
 'search_raid_controller':'设施存储服务器的阵列控制卡，独立散热片旁装有缓存小板和多组内部数据接口。成套模块负责组织存储设备，完整板卡较为珍贵。',
 'search_compute_accelerator':'设施计算中心的专用加速模块，长条被动散热通道依靠服务器风道带走热量。厚背板与供电结构保存完整，是机房中价值较高的成套计算硬件。',
}
path=PROJECT/'Content/ColdSteelData/items.json'
raw=path.read_text('utf-8-sig');catalog=json.loads(raw)
added=[];published=[]
for icon in ICONS['icons']:
    identifier=icon['id'];item=ITEMS[identifier]
    definition=dict(id=identifier,name=item['name'],category='material',type='机房设备',loot_group='server_equipment',
        rarity=item['rarity'],price=item['sell_souls'],sell_souls=item['sell_souls'],desc=DESC[identifier],
        grid_w=item['grid_w'],grid_h=item['grid_h'],stack=1,stack_max=item['max_stack'],maxStack=item['max_stack'],
        inventory_unit=item['inventory_unit'],icon=icon['ue_icon'],ue_icon=icon['ue_icon'],icon_fallback=item['name'],
        world_mesh=MESHES[identifier]['path'])
    if identifier in catalog:
        if catalog[identifier]!=definition:raise RuntimeError('Preserve existing differing definition '+identifier)
    else:
        body=json.dumps(definition,ensure_ascii=False,indent=2)
        added.append('  '+json.dumps(identifier)+': '+body.replace('\n','\n  '))
    published.append(definition)
    item.update(status='runtime_catalog_and_art_integrated_loot_pending',ue_icon=icon['ue_icon'])
if added:
    close=raw.rfind('}')
    path.write_text(raw[:close].rstrip()+',\n'+',\n'.join(added)+'\n'+raw[close:],encoding='utf-8')
delivery=DESIGN['delivery']
delivery['runtime_added_item_ids']=list(dict.fromkeys(delivery.get('runtime_added_item_ids',[])+[i['id'] for i in published]))
delivery.update(server_icons_created=True,server_runtime_items_added=True,
    server_inventory_icons='SourceAssets/SearchServerEquipment20261013/inventory_icons.json')
DESIGN_PATH.write_text(json.dumps(DESIGN,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt=dict(stage='runtime_catalog_and_icons_saved',items=published,loot_pool_changed=False,
    player_inventory_changed=False,sale_system_implemented=False,tests_run=False,
    icon_contract='Transparent RGBA PNG at grid aspect ratio; existing ue_icon cache and drawing path',
    legacy_instance_migration_required=False)
(ROOT/'Receipts/inventory-integration.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SERVER_INVENTORY_SAVED',[(i['id'],i['grid_w'],i['grid_h']) for i in published])
