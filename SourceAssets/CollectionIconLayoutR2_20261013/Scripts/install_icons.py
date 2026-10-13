"""Publish the requested icon artwork at its existing runtime paths."""
from pathlib import Path
import json,shutil
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
manifest=json.loads((ROOT/'model_manifest.json').read_text('utf-8'))
rendered=json.loads((ROOT/'inventory_icons.json').read_text('utf-8'))
if rendered['stage']!='icons_saved':raise RuntimeError('Icon production is still in progress')
catalog=json.loads((PROJECT/'Content/ColdSteelData/items.json').read_text('utf-8-sig'))
for icon in rendered['icons']:
    spec=manifest['assets'][icon['id']]
    if catalog[icon['id']]['ue_icon']!=spec['ue_icon']:raise RuntimeError('Preserve changed item icon reference: '+icon['id'])
    if Path(icon['runtime_icon']).read_bytes()!=Path(spec['previous_icon']).read_bytes():
        raise RuntimeError('Preserve parallel icon change: '+icon['id'])
    for alias in spec['legacy_aliases']:
        if Path(alias['path']).read_bytes()!=Path(alias['backup']).read_bytes():raise RuntimeError('Preserve changed legacy icon '+alias['path'])
report=dict(stage='installing',icons=[],equipment_changed=False,weapons_changed=False,
            footprints_changed={'search_graphics_card':{'from':[3,2],'to':[2,1]}},model_assets_changed=False,tests_run=False,game_started=False)
receipt=ROOT/'Receipts/installation.json'
for icon in rendered['icons']:
    shutil.copy2(icon['file'],icon['runtime_icon'])
    for alias in manifest['assets'][icon['id']]['legacy_aliases']:shutil.copy2(icon['file'],alias['path'])
    report['icons'].append(icon)
    receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
design_path=PROJECT/'Docs/Gameplay/search-item-catalog-v2-20261012.json'
design=json.loads(design_path.read_text('utf-8'))
applied={icon['id']:icon for icon in rendered['icons']}
for item in design['items']:
    if item['id'] in applied:item['icon_orientation']=applied[item['id']]['orientation']['mode']
design['rules']['collection_icon_orientation']='收集物条状图标按占格水平或竖直居中；细长的1×1物品也水平居中。2×2、3×2等较宽形态恢复原背包图标的作者视角。武器、可穿戴装备以及玩家主动旋转占格的交互沿用原规则。'
design['delivery']['collection_icon_orientation']='Docs/Art/collection-icon-layout-r2-20261013.md'
design_path.write_text(json.dumps(design,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report.update(stage='icons_installed',count=len(report['icons']),
    horizontal_count=sum(i['orientation']['mode']=='horizontal_centered' for i in report['icons']),
    vertical_count=sum(i['orientation']['mode']=='vertical_centered' for i in report['icons']),
    standard_count=sum(i['orientation']['mode']=='standard_inventory' for i in report['icons']),
    reload='Existing texture-cache paths are preserved; restart the game to reload PNG content')
receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('COLLECTION_ICONS_INSTALLED',report['count'],'horizontal',report['horizontal_count'],'vertical',report['vertical_count'],'standard',report['standard_count'])
