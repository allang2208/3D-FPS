"""Publish the user's pointed-head table and 15 percent physical defense penetration."""
import json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
option=runpy.run_path(str(P.parent/'BuildV1/catalog.py'))['OPTION']
path=ROOT/'Content/ColdSteelData/common-hammer-heads.json'
catalog=json.loads(path.read_text(encoding='utf-8-sig'))
target=next(o for o in catalog['options'] if o['id']==option['id'])
for key in ('stats','effects','special_effects'):target[key]=option[key]
path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'balance_receipt.json').write_text(json.dumps({
 'status':'user_table_saved','date':'2026-10-15','option_id':option['id'],'slot':'hammer_heads',
 'stats':option['stats'],'effects':option['effects'],
 'penetration':'additive physical defense penetration fraction; existing total clamp 0..1',
 'native_build_required':True,'asset_reimport_required':False,'game_tested':False
},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('POINTED_HAMMER_USER_BALANCE_V2_SAVED',flush=True)
