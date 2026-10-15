"""Publish the legendary head's direct attributes from its authoring catalogue."""
import json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
option=runpy.run_path(str(P.parent/'BuildV1/catalog.py'))['OPTION']
path=ROOT/'Content/ColdSteelData/warhammer-gunsmith.json'
catalog=json.loads(path.read_text(encoding='utf-8-sig'))
column=next(c for c in catalog['columns'] if c['key']=='hammer_heads')
target=next(o for o in column['options'] if o['id']==option['id'])
for key in ('stats','effects','special_effects'):target[key]=option[key]
path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'balance_receipt.json').write_text(json.dumps({
 'status':'saved','date':'2026-10-15','weapon':'ue_steel_warhammer',
 'slot':'hammer_heads','option_id':option['id'],'tier':'legendary','exclusive':True,
 'values_source':'assistant_initial_balance_requested_by_user',
 'stats':option['stats'],'effects':option['effects'],
 'native_build_required':False,'asset_reimport_required':False,'game_tested':False
},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('METEOR_CORE_BALANCE_V1_SAVED',flush=True)
