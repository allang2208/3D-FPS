"""Install saved string assets into the current catalog; preserve other columns."""
from pathlib import Path
import json,shutil
P=Path(__file__).parent;ROOT=P.parents[1]
series=json.loads((P/'series.json').read_text(encoding='utf8'))
assets=json.loads((P/'import-receipt.json').read_text(encoding='utf8'))['saved']
backup=ROOT/'Saved/BowStringVariants20260927/Before';backup.mkdir(parents=True,exist_ok=True)
path=ROOT/'Content/ColdSteelData/bow-gunsmith.json'
text=path.read_text(encoding='utf-8-sig');data=json.loads(text)
column=next(c for c in data['columns'] if c['key']=='string')
for row in series['variants']:
    icon='bow_dark_string_'+row['id']
    for name in (row['material'],icon):
        if name not in assets:raise RuntimeError('Asset not saved '+name)
    option={'id':row['id'],'name':row['display_name'],'description':row['description'],
            'appearance':row['appearance'],'visual':{'bow_part_string_material':assets[row['material']],
            'bow_part_string_radius_cm':series['radius_cm']},'stats':row['stats']}
    index=next((i for i,o in enumerate(column['options']) if o['id']==row['id']),None)
    if index is None:column['options'].append(option)
    else:column['options'][index]=option
    dest=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/(icon+'.png')
    if dest.exists() and not (backup/dest.name).exists():shutil.copy2(dest,backup/dest.name)
    shutil.copy2(P/'Icons'/(icon+'.png'),dest)
for col in data['columns']:
    for option in col['options']:
        if 'description' in option:option['description']=option['description'].replace('箭速','子弹速度')
if not (backup/path.name).exists():shutil.copy2(path,backup/path.name)
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
config=ROOT/'Config/DefaultGame.ini';text=config.read_text(encoding='utf-8-sig')
line='+DirectoriesToAlwaysCook=(Path="'+series['asset_directory']+'")'
if line not in text:
    if not (backup/config.name).exists():shutil.copy2(config,backup/config.name)
    section='[/Script/UnrealEd.ProjectPackagingSettings]'
    if section not in text:raise RuntimeError('Missing packaging section')
    config.write_text(text.replace(section,section+'\n'+line,1),encoding='utf8')
(P/'install-receipt.json').write_text(json.dumps({'slot':'string','ids':[r['id'] for r in series['variants']],
    'saved_assets':assets,'existing_equipment_changed':False,'gameplay_tested':False},ensure_ascii=False,indent=2),encoding='utf8')
print('BOW_STRING_CATALOG_INSTALLED',len(series['variants']))
