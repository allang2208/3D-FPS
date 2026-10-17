"""Extend only M870's optic options; shared inventory IDs and stats are reused."""
import json,copy
from pathlib import Path
P=Path(__file__).parents[2]/'Content/ColdSteelData/gunsmith.json'
text=P.read_text(encoding='utf-8-sig');data=json.loads(text)
donor=next(w for w in data['weapons'] if w['id']=='ue_super90')
marker=text.index('"id": "ue_m870"');start=text.rfind('{',0,marker)
weapon,end=json.JSONDecoder().raw_decode(text[start:])
known={x['id'] for x in weapon['options']['optic']}
for option in donor['options']['optic']:
    if option['id']=='false' or option['id'] in known:continue
    weapon['options']['optic'].append(copy.deepcopy(option))
# thermal_scope is injected by common_options.optic for every weapon.
indent=text[text.rfind('\n',0,start)+1:start]
block=json.dumps(weapon,ensure_ascii=False,indent=2).replace('\n','\n'+indent)
P.write_text(text[:start]+block+text[start+end:],encoding='utf-8')
print('M870_OPTIC_OPTIONS_REGISTERED',flush=True)
