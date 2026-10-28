"""Publish only the weapon-switch exit rule, preserving the current catalog."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
line='周期｜状态期间不续时、不再次蓄能；切换武器立即退出狂战士并清空蓄能，切回后重新累计；死亡同样清空。'
paths=[ROOT/'Content/ColdSteelData/kukri-gunsmith.json',
       ROOT/'SourceAssets/KukriComponentVariants20261026/kukri-gunsmith.json',
       ROOT/'SourceAssets/KukriBerserker20261028/published-option.json']
for path in paths:
    data=json.loads(path.read_text('utf-8-sig'))
    if 'columns' in data:
        column=next(c for c in data['columns'] if c['key']=='blade_2')
        option=next(o for o in column['options'] if o['id']=='berserker_rune')
    else:option=data
    effects=option['special_effects']
    index=next(i for i,text in enumerate(effects) if text.startswith('周期｜'))
    effects[index]=line
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Updated only the berserker weapon-switch description in all three catalogs.')
