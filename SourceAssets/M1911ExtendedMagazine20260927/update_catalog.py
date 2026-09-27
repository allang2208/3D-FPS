"""Publish only the M1911 definition, preserving concurrent catalog work."""
import json
from pathlib import Path
O=Path(__file__).parent;p=O.parents[1]/'Content/ColdSteelData/gunsmith.json'
text=p.read_text(encoding='utf-8-sig');data=json.loads(text)
weapon=next(w for w in data['weapons'] if w['id']=='ue_m1911')
factory={'id':'false','name':'原厂弹匣','description':'M1911 原厂单排弹匣，保留紧凑外形。','effects':[],'stats':{}}
ext={'id':'ext_mag','name':'扩容弹匣','description':'沿原厂单排壳体向下延长，保留插接接口、抓握区与独立底板。',
     'effects':[{'text':'弹匣容量增加3发','benefit':1},
                {'text':'装填耗时更长','benefit':-1},
                {'text':'开镜耗时增加5%','benefit':-1}],
     'stats':{'mag_delta':3,'reload_mult':1.1,'ads_percent':.05}}
if 'magazine' not in weapon['allowed']:weapon['allowed'].append('magazine')
options=weapon['options'].setdefault('magazine',[])
for option in [factory,ext]:
    prior=next((i for i,a in enumerate(options) if a['id']==option['id']),None)
    if prior is None:options.append(option)
    else:options[prior]=option
for trait in weapon.get('traits',[]):
    if trait.get('icon')=='neutral' and '改造' in trait.get('text',''):
        trait['text']='瞄具、枪口、弹匣、扳机与战术挂件全部可改造'
    elif trait.get('icon')=='mechanic':
        trait['text']=trait['text'].replace('7 发单排弹匣','原厂 7 发单排弹匣') if '原厂' not in trait['text'] else trait['text']
idpos=text.index('"id": "ue_m1911"');start=text.rfind('{',0,idpos)
_,length=json.JSONDecoder().raw_decode(text[start:]);end=start+length
backup=O/'catalog_before_m1911.json'
if not backup.exists():backup.write_text(text[start:end],encoding='utf-8')
encoded=json.dumps(weapon,ensure_ascii=False,indent=2).splitlines()
replacement=encoded[0]+'\n'+'\n'.join('    '+line for line in encoded[1:])
if p.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Catalog changed while preparing M1911 edit')
p.write_text(text[:start]+replacement+text[end:],encoding='utf-8')
(O/'catalog_change.json').write_text(json.dumps({'definition':'ue_m1911','slot':'magazine','id':'ext_mag',
    'base_capacity':weapon['base']['mag_size'],'capacity':weapon['base']['mag_size']+3,
    'stats':ext['stats'],'game_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('M1911_EXTMAG_CATALOG_SAVED',flush=True)
