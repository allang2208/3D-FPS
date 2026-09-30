"""Add only the 201 magazine slot; preserve unrelated catalog work."""
import json
from pathlib import Path
O=Path(__file__).parent
path=O.parents[2]/'Content/ColdSteelData/gunsmith.json'
text=path.read_text(encoding='utf-8-sig')
start=text.rfind('{',0,text.index('"id": "ue_lmg201"'))
weapon,length=json.JSONDecoder().raw_decode(text[start:])
if 'magazine' not in weapon['allowed']:weapon['allowed'].append('magazine')
weapon['traits'][0]['text']='全自动射击，使用5.8毫米弹药；原厂30发弹匣，可改用100发弹药箱。'
weapon['traits'][1]['text']='原厂双脚架支持在适合的支撑面架设；枪匠可更换瞄具、枪口、供弹组件或卸下脚架。'
normal=6.5/weapon['base']['reload_time']
empty=6.6/weapon['base']['empty_reload_time']
weapon['options']['magazine']=[
 {'id':'false','name':'原厂弹匣','description':'使用30发弹匣与原有弹匣换弹动作。','effects':[],'stats':{}},
 {'id':'lmg201_ammo_box','name':'弹药箱','description':'切换为100发弹箱供弹；换弹时开启机匣盖，更换弹箱、铺放弹链并合盖，空仓时继续拉栓。',
  'effects':[{'text':'载弹量增加70发','benefit':1},
             {'text':'普通换弹耗时增加95%','benefit':-1},
             {'text':'空仓换弹耗时增加53.8%','benefit':-1}],
  'stats':{'mag_delta':70,'reload_mult':normal,'empty_reload_mult':empty}}
]
formatted=json.dumps(weapon,ensure_ascii=False,indent=2).replace('\n','\n      ')
path.write_text(text[:start]+formatted+text[start+length:],encoding='utf8')
(O/'catalog_authoring.json').write_text(json.dumps({'weapon':weapon['id'],'slot':'magazine','part':'lmg201_ammo_box','capacity':100,'normal_seconds':6.5,'empty_seconds':6.6,'capacity_is_game_setting':True},indent=2),encoding='utf8')
print('201_BELTFEED_CATALOG_WRITTEN')
