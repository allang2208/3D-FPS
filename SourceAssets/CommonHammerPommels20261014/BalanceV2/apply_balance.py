"""Publish the user's final pommel balance and matching effect descriptions."""
import json, runpy
from pathlib import Path
P = Path(__file__).resolve().parent
ROOT = P.parents[2]
options = runpy.run_path(str(P.parent/'BuildV1/catalog.py'))['OPTIONS']
path = ROOT/'Content/ColdSteelData/common-hammer-pommels.json'
data = json.loads(path.read_text(encoding='utf-8-sig'))
incoming = {o['id']:o for o in options}
for option in data['options']:
    if option['id'] in incoming:
        option['stats'] = incoming[option['id']]['stats']
        option['effects'] = incoming[option['id']]['effects']
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'balance_receipt.json').write_text(json.dumps({
    'status':'user_table_saved', 'weapon':'ue_steel_warhammer', 'slot':'pommel',
    'stats':{o['id']:o['stats'] for o in options}, 'martial_cooldown_scope':['whirlwind','swordUppercut'],
    'cooldown_formula':'base * skill_cooldown_mult * martial_cooldown_mult',
    'magic_cooldown_affected_by_pommel':False, 'asset_reimport_required':False,
    'native_build_required':True, 'game_tested':False
},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('USER_POMMEL_BALANCE_SAVED')
