"""Publish only the 201 magazine option after its assets have saved."""
import json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];path=P/'Content/ColdSteelData/gunsmith.json'
def publish():
 text=path.read_bytes().decode('utf-8');pos=text.index('"id": "ue_lmg201"');begin=text.rfind('{',0,pos)
 weapon,length=json.JSONDecoder().raw_decode(text[begin:]);before=O/'Before/gunsmith201.json';before.parent.mkdir(exist_ok=True)
 if not before.exists():before.write_text(json.dumps(weapon,ensure_ascii=False,indent=2),encoding='utf8')
 if 'magazine' not in weapon['allowed']:weapon['allowed'].insert(2,'magazine')
 weapon['options']['magazine']=[
  {'id':'false','name':'原厂弹匣','description':'30 发标准弹匣，使用原装弹匣换弹动作。','effects':[],'stats':{}},
  {'id':'lmg201_cloth_box','name':'125 发布料弹药箱','description':'布料弹箱与弹链供弹；左手开盖、换箱、铺链、合盖后回握。','effects':[{'text':'装弹量增加95发','benefit':1},{'text':'换弹基础耗时6.2秒','benefit':-1}],'stats':{'mag_delta':95,'reload_mult':6.2/weapon['base']['reload_time'],'empty_reload_mult':6.2/weapon['base']['empty_reload_time']}}]
 weapon['traits'][0]['text']='全自动射击，使用5.8毫米弹药；原厂30发弹匣，可改装125发布料弹药箱。'
 replacement=json.dumps(weapon,ensure_ascii=False,indent=2);replacement=replacement.replace('\n','\n    ')
 if '\r\n' in text:replacement=replacement.replace('\n','\r\n')
 path.write_bytes((text[:begin]+replacement+text[begin+length:]).encode('utf8'))
 (O/'catalog_saved.json').write_text(json.dumps({'file':str(path),'weapon':'ue_lmg201','option':'lmg201_cloth_box','capacity':125,'original_magazine_retained':True,'legacy_metal_box_migration_unchanged':True},indent=2))
 print('CLOTH33_CATALOG_SAVED',flush=True)
if __name__=='__main__':publish()
