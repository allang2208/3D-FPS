"""Bind authored maintenance assets and icons to catalog items; recipes remain staged design."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
ICONS=json.loads((ROOT/'inventory_icons.json').read_text('utf-8'))
MODELS=json.loads((ROOT/'model_manifest.json').read_text('utf-8'))
MODEL_BY_ID={spec['id']:spec for spec in MODELS['assets'].values()}
IMPORT=json.loads((ROOT/'Receipts/ue-import.json').read_text('utf-8'))
MESHES={mesh['item_id']:mesh for mesh in IMPORT['meshes']}
DESIGN_PATH=PROJECT/'Docs/Gameplay/search-item-catalog-v2-20261012.json'
DESIGN=json.loads(DESIGN_PATH.read_text('utf-8'))
ITEMS={i['id']:i for i in DESIGN['items']}
DESC={
 'search_forging_alloy_blank':'设施检修库储备的整块合金坯料，加工端面保留检验痕迹，中段以保护纸包覆。供铁匠台进一步锻制剑类装备，按整块材料保管。',
 'search_assembly_component_box':'设施检修库配发的装配零件盒，分格纸托集中收纳紧固件、弹簧、定位件和垫圈。为枪械组装准备的成套材料，整盒领用。',
 'search_resin_adhesive':'木工材料柜保存的双腔树脂胶包，树脂与固化剂由热封隔带分开，封边保留撕口。作为层压木件胶合的配套耗材，按完整胶包保存。',
 'search_laminated_strip':'经过分层胶合与整形的木条，以两道纸带捆成一束，端部保留层压纹路。供木工台加工弓臂，干燥储存可保持材料形态。',
 'search_precision_mechanism':'检修库成组封装的精加工机件，衬套、阶梯短轴和齿形件分别嵌入防震托。为需要精密装配的枪械准备的配套材料，按整组保管。',
}
runtime_path=PROJECT/'Content/ColdSteelData/items.json'
raw=runtime_path.read_text('utf-8-sig');runtime=json.loads(raw)
published=[];appended=[]
for icon in ICONS['icons']:
    identifier=icon['id'];item=ITEMS[identifier];model=MODEL_BY_ID[identifier]
    definition=dict(id=identifier,name=item['name'],category='material',type='检修材料',loot_group='maintenance',
        rarity=item['rarity'],price=item['sell_souls'],sell_souls=item['sell_souls'],desc=DESC[identifier],
        grid_w=item['grid_w'],grid_h=item['grid_h'],stack=1,stack_max=item['max_stack'],maxStack=item['max_stack'],
        inventory_unit=item['inventory_unit'],icon=icon['ue_icon'],ue_icon=icon['ue_icon'],icon_fallback=item['name'],
        world_mesh=MESHES[identifier]['path'])
    if identifier in runtime:
        if runtime[identifier]!=definition:raise RuntimeError('Preserve differing existing item '+identifier)
    else:
        block=json.dumps(definition,ensure_ascii=False,indent=2)
        appended.append('  '+json.dumps(identifier)+': '+block.replace('\n','\n  '))
    published.append(definition)
    item.update(status='runtime_catalog_and_art_integrated_recipes_and_loot_pending',ue_icon=icon['ue_icon'])
    item['model'].update(status='ue_assets_saved_and_installed',
        actual_dimensions_cm=model['actual_dimensions_cm'],triangles_lod0=model['triangles_lod0'],texture_size=model['size'],
        source=str(Path(model['source']).relative_to(PROJECT)).replace('\\','/'),
        glb=str(Path(model['glb']).relative_to(PROJECT)).replace('\\','/'),
        fbx=str(Path(model['fbx']).relative_to(PROJECT)).replace('\\','/'),
        ue_mesh=MESHES[identifier]['path'],ue_material=MESHES[identifier]['material'])
if appended:
    close=raw.rfind('}');raw=raw[:close].rstrip()+',\n'+',\n'.join(appended)+'\n'+raw[close:]
    runtime_path.write_text(raw,encoding='utf-8')
delivery=DESIGN['delivery']
for field in ('modeled_item_ids','runtime_added_item_ids'):
    delivery[field]=list(dict.fromkeys(delivery.get(field,[])+[i['id'] for i in published]))
delivery.update(maintenance_models_created=True,maintenance_icons_created=True,
    maintenance_model_delivery='Docs/Art/search-maintenance-models-20261012.md',
    maintenance_icons='SourceAssets/SearchMaintenance20261012/inventory_icons.json')
DESIGN_PATH.write_text(json.dumps(DESIGN,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt=dict(stage='runtime_catalog_and_art_saved',items=published,loot_pool_changed=False,
    runtime_recipes_changed=False,player_inventory_changed=False,tests_run=False,
    recipe_design={i['id']:ITEMS[i['id']]['recipe_uses'] for i in published})
(ROOT/'Receipts/inventory-integration.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('MAINTENANCE_INVENTORY_SAVED',[(i['id'],i['grid_w'],i['grid_h'],i['maxStack']) for i in published])
