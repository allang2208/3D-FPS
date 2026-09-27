"""Append new grip choices to the current catalog without changing equipped parts."""
from pathlib import Path
import json,shutil,hashlib
P=Path(__file__).parent;ROOT=P.parents[1]
BACK=ROOT/'Saved/BowGripSeries20260927/Before';BACK.mkdir(parents=True,exist_ok=True)
rows=json.loads((P/'series.json').read_text(encoding='utf8'))['variants']
assets=json.loads((P/'import-receipt.json').read_text(encoding='utf8'))['saved']
path=ROOT/'Content/ColdSteelData/bow-gunsmith.json'
data=json.loads(path.read_text(encoding='utf-8-sig'))
grip=next(c for c in data['columns'] if c['key']=='grip')
changes=[]
for row in rows:
    icon='bow_dark_grip_'+row['id']
    for required in (row['mesh'],row['material'],icon):
        if required not in assets:raise RuntimeError('Asset not yet saved '+required)
    option={'id':row['id'],'name':row['display_name'],'description':row['description'],
        'appearance':row['appearance'],'visual':{
            'bow_part_grip_mesh':assets[row['mesh']], 'bow_part_grip_material':'',
            'bow_part_grip_rods':0,'bow_part_grip_scale':1.0},'stats':row['stats']}
    index=next((i for i,o in enumerate(grip['options']) if o['id']==row['id']),None)
    if index is None:grip['options'].append(option)
    else:grip['options'][index]=option
    source=P/'Icons'/(icon+'.png');dest=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/(icon+'.png')
    if dest.exists() and not (BACK/dest.name).exists():shutil.copy2(dest,BACK/dest.name)
    shutil.copy2(source,dest)
    changes.append({'id':row['id'],'name':row['display_name'],'mesh':assets[row['mesh']],
        'icon':str(dest),'icon_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'stats':row['stats']})
if not (BACK/path.name).exists():shutil.copy2(path,BACK/path.name)
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
config=ROOT/'Config/DefaultGame.ini';text=config.read_text(encoding='utf-8-sig')
line='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/DarkBow20260925/GripSeriesV20")'
if line not in text:
    if not (BACK/config.name).exists():shutil.copy2(config,BACK/config.name)
    section='[/Script/UnrealEd.ProjectPackagingSettings]'
    if section not in text:raise RuntimeError('Packaging section missing')
    config.write_text(text.replace(section,section+'\n'+line,1),encoding='utf8')
(P/'install-receipt.json').write_text(json.dumps({'variants':changes,'slot':'grip',
    'base_bow_changed':False,'native_code_changed':False,'gameplay_tested':False},ensure_ascii=False,indent=2),encoding='utf8')
print('BOW_GRIP_SERIES_INSTALLED',len(changes))
