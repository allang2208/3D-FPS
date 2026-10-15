"""Publish the requested ground-wave effect without changing the four existing stats."""
import json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
option=runpy.run_path(str(P.parent/'BuildV1/catalog.py'))['OPTION']
path=ROOT/'Content/ColdSteelData/warhammer-gunsmith.json'
catalog=json.loads(path.read_text(encoding='utf-8-sig'))
column=next(c for c in catalog['columns'] if c['key']=='hammer_heads')
target=next(o for o in column['options'] if o['id']==option['id'])
target['stats']['shockwave_radius_mult']=option['stats']['shockwave_radius_mult']
target['special_effects']=option['special_effects']
path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'effect_receipt.json').write_text(json.dumps({
 'status':'saved','weapon':'ue_steel_warhammer','slot':'hammer_heads','option_id':'meteor_core',
 'shockwave_radius_mult':option['stats']['shockwave_radius_mult'],'base_radius_cm':300,'modified_radius_cm':450,
 'scope':['charged heavy ground wave','sprint ground wave'],'special_effects':option['special_effects'],
 'damage_and_visuals_share_radius':True,'radius_replicated_by':'AWarhammerShockwave.MaxRadius',
 'native_build_required':True,'asset_reimport_required':False,'game_tested':False
},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('METEOR_CORE_SHOCKWAVE_RANGE_SAVED',flush=True)
