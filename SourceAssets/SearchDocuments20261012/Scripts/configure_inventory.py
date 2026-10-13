"""Publish the four approved document collectibles and their inventory art."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
ICONS = json.loads((ROOT/'inventory_icons.json').read_text('utf-8'))
MESHES = {m['item_id']:m for m in json.loads((ROOT/'Receipts/ue-import.json').read_text('utf-8'))['meshes']}
DESIGN_PATH = PROJECT/'Docs/Gameplay/search-item-catalog-v2-20261012.json'
DESIGN = json.loads(DESIGN_PATH.read_text('utf-8-sig'))
ITEMS = {i['id']:i for i in DESIGN['items']}
DESCRIPTIONS = {
    'search_usb_drive':'设施管理处用于转交电子资料的便携存储器，金属外壳上保留编号和归属标签。接口与封装完整，其中保存的行政记录具有回收价值。',
    'search_archive_tape':'设施档案室定期封存的数据备份磁带，盒面标有卷号与归档日期。写保护开关保持锁定，完整的备份介质适合作为资料收集品带回。',
    'search_encrypted_archive_case':'设施管理处移交重要资料的防震盒，锁扣与封签保护着编号介质和密封文件袋。内容与封存状态完整，具有较高回收价值。',
    'search_certified_admin_archive':'设施综合事务室整理的行政卷宗，连续页码、签章和交接封条保留了资料的完整身份。纸张以棉绳装订，整套档案具有回收价值。',
}
path = PROJECT/'Content/ColdSteelData/items.json'
raw = path.read_text('utf-8-sig')
catalog = json.loads(raw)
published = []
new_entries = []
for icon in ICONS['icons']:
    identifier = icon['id']
    design = ITEMS[identifier]
    definition = dict(id=identifier, name=design['name'], category='material',
        type='文件材料', loot_group='documents', desc=DESCRIPTIONS[identifier],
        rarity=design['rarity'], price=design['sell_souls'], sell_souls=design['sell_souls'],
        grid_w=icon['grid_w'], grid_h=icon['grid_h'], stack=1, stack_max=1, maxStack=1,
        icon=icon['ue_icon'], ue_icon=icon['ue_icon'], icon_fallback=design['name'],
        world_mesh=MESHES[identifier]['path'])
    if identifier in catalog:
        if catalog[identifier] != definition:
            raise RuntimeError('Existing definition differs; preserve and reconcile: '+identifier)
    else:
        block = json.dumps(definition, ensure_ascii=False, indent=2)
        new_entries.append('  '+json.dumps(identifier)+': '+block.replace('\n','\n  '))
    published.append(definition)
    design.update(grid_w=icon['grid_w'], grid_h=icon['grid_h'],
                  status='runtime_catalog_and_icons_integrated_loot_pending',
                  ue_icon=icon['ue_icon'])
if new_entries:
    closing = raw.rfind('}')
    raw = raw[:closing].rstrip()+',\n'+',\n'.join(new_entries)+'\n'+raw[closing:]
    path.write_text(raw, encoding='utf-8')
DESIGN['rules']['sale_item_floor_v2']['exception'] = '用户确认签章行政档案占格2×2，保留900灵魂设计价，225灵魂/格；不因扩格自动涨价。'
DESIGN['delivery'].update(new_runtime_items_added=True,
    runtime_added_item_ids=[d['id'] for d in published], icons_created=True,
    loot_pool_changed=False, inventory_icons='SourceAssets/SearchDocuments20261012/inventory_icons.json')
DESIGN_PATH.write_text(json.dumps(DESIGN,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt = dict(stage='runtime_catalog_and_icons_saved', items=published,
    loot_pool_changed=False, player_inventory_changed=False,
    sale_system_implemented=False, tests_run=False,
    icon_contract='512x512 RGBA PNG; ue_icon uses existing cached catalog texture loader',
    new_definitions=True, legacy_instance_migration_required=False)
(ROOT/'Receipts/inventory-integration.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('DOCUMENT_INVENTORY_CATALOG_SAVED', [(d['id'],d['grid_w'],d['grid_h']) for d in published])
