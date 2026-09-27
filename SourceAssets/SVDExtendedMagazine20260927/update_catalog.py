"""Add SVD's own magazine choices without rewriting unrelated weapon entries."""
import copy,json
from pathlib import Path
O=Path(__file__).parent
p=O.parents[1]/'Content/ColdSteelData/gunsmith.json'
text=p.read_text(encoding='utf-8-sig');data=json.loads(text)
svd=next(w for w in data['weapons'] if w['id']=='ue_svd')
donor=next(w for w in data['weapons'] if w['id']=='ue_m16a2')
ext=copy.deepcopy(next(a for a in donor['options']['magazine'] if a['id']=='ext_mag'))
ext['description']='沿 SVD 原厂冲压壳体延长，保留入枪接口、口部内腔、抓握区域与独立底板。'
factory={'id':'false','name':'原厂弹匣','description':'恢复 SVD 原厂短弹匣及其内壁与底板。','effects':[],'stats':{}}
if 'magazine' not in svd['allowed']:svd['allowed'].append('magazine')
svd['options']['magazine']=[factory,ext]
for trait in svd.get('traits',[]):
    if trait.get('icon')=='neutral' and '改造' in trait.get('text','') and '弹匣' not in trait['text']:
        trait['text']=trait['text'].replace('可改造','与弹匣可改造').replace('前握把与弹匣','前握把、弹匣')
idpos=text.index('"id": "ue_svd"');start=text.rfind('{',0,idpos)
_,length=json.JSONDecoder().raw_decode(text[start:]);end=start+length
(O/'catalog_before_svd.json').write_text(text[start:end],encoding='utf-8')
encoded=json.dumps(svd,ensure_ascii=False,indent=2).splitlines()
replacement=encoded[0]+'\n'+'\n'.join('    '+line for line in encoded[1:])
if p.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Catalog changed while preparing SVD edit')
p.write_text(text[:start]+replacement+text[end:],encoding='utf-8')
(O/'catalog_change.json').write_text(json.dumps({'definition':'ue_svd','slot':'magazine','ids':['false','ext_mag'],
    'stats':ext['stats'],'base_capacity':svd['base']['mag_size'],'capacity':svd['base']['mag_size']+ext['stats']['mag_delta'],
    'stats_source':'Existing ext_mag option; effects/stats preserved verbatim','game_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('SVD_EXTMAG_CATALOG_SAVED')
