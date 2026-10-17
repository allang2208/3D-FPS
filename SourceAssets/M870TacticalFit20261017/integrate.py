"""Update only M870's tactical choices and remove its rear-grip modification."""
import copy,json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];path=P/'Content/ColdSteelData/gunsmith.json'
text=path.read_text(encoding='utf-8-sig');catalog=json.loads(text)
donor=next(w for w in catalog['weapons'] if w['id']=='ue_super90')
start=text.rfind('{',0,text.index('"ue_m870"'));weapon,length=json.JSONDecoder().raw_decode(text[start:])
old=copy.deepcopy(weapon)
weapon['allowed']=[s for s in weapon['allowed'] if s!='reargrip']
weapon['options'].pop('reargrip',None)
weapon.get('default_parts',{}).pop('reargrip',None)
options=weapon['options']['tactical']
for value in donor['options']['tactical']:
    if value['id'] in ('laser','flashlight') and not any(v['id']==value['id'] for v in options):options.append(copy.deepcopy(value))
indent=len(text[text.rfind('\n',0,start)+1:start]);replacement=json.dumps(weapon,ensure_ascii=False,indent=2).replace('\n','\n'+' '*indent)
if path.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Catalog changed during merge')
path.write_text(text[:start]+replacement+text[start+length:],encoding='utf-8')
(O/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_m870','removed_slot':'reargrip','removed_options':old['options'].get('reargrip',[]),'tactical_options':options,'blessed_laser':'existing common_options tactical','legacy_parts':'Installed and Calculate use Normalize; removed slot no longer resolves','spread_mult':weapon['base']['spread_mult']},ensure_ascii=False,indent=2),encoding='utf-8')
print('M870_TACTICAL_CATALOG_SAVED')
