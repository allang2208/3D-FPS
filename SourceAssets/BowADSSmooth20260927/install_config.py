"""V18: closer ADS and one smooth pose/zoom clock; no asset or gameplay tests."""
import json
from pathlib import Path

P=Path(__file__).parent
ROOT=P.parents[1]
path=ROOT/'Content/ColdSteelData/bows.json'
data=json.loads(path.read_text(encoding='utf-8-sig'))
bow=data['bow_dark']
changes={'bow_ads_sight_distance_cm':60.,'bow_ads_rest_cm':'63,10,-12',
         'bow_ads_in_seconds':.30,'bow_ads_out_seconds':.26}
changed=any(bow.get(key)!=value for key,value in changes.items())
bow.update(changes)
bow['bow_presentation_revision']=max(29,int(bow.get('bow_presentation_revision',0))+int(changed))
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
path=ROOT/'Content/ColdSteelData/bow-gunsmith.json'
data=json.loads(path.read_text(encoding='utf-8-sig'))
sight=next(c for c in data['columns'] if c['key']=='sight')
for option in sight['options']:
    if option['id']=='no_sight':option['visual']['bow_ads_rest_cm']='60,0,0'
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(P/'install-receipt.json').write_text(json.dumps({'revision':bow['bow_presentation_revision'],
    'settings':changes,'ads_toward_camera_cm':7.,'runtime_tested':False,'rendered':False},indent=2),encoding='utf8')
print('BOW_ADS_SMOOTH_V18_ACTIVATED revision='+str(bow['bow_presentation_revision']))
