"""Add the shared large-drum option to 201, preserving all other options."""
import json,copy
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];file=P/'Content/ColdSteelData/gunsmith.json';data=json.loads(file.read_text(encoding='utf-8-sig'))
donor=next(w for w in data['weapons'] if w['id']=='ue_akm')
target=next(w for w in data['weapons'] if w['id']=='ue_lmg201')
option=copy.deepcopy(next(o for o in donor['options']['magazine'] if o['id']=='large_drum'))
option['description']='适配 201 弹匣井的鼓式弹匣；旧鼓自然落下，左手托住新鼓装入。'
choices=target['options']['magazine'];choices[:]=[o for o in choices if o['id']!='large_drum'];choices.append(option)
file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(O/'catalog_receipt.json').write_text(json.dumps({'definition':'ue_lmg201','option':option,'other_magazines':[o['id'] for o in choices]},ensure_ascii=False,indent=2),encoding='utf8')
config=P/'Config/DefaultGame.ini';text=config.read_text(encoding='utf-8-sig');entry='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/LMG201/Drum46")'
if entry not in text:
    section='[/Script/UnrealEd.ProjectPackagingSettings]'
    text=text.replace(section,section+'\n'+entry,1);config.write_text(text,encoding='utf8')
print('DRUM46_CATALOG_SAVED')
