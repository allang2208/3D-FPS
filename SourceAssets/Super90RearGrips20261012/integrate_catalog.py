import json,copy
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];path=P/'Content/ColdSteelData/gunsmith.json';text=path.read_text(encoding='utf-8-sig');data=json.loads(text)
source=next(w for w in data['weapons'] if w['id']=='ue_m4a1')
start=text.rfind('{',0,text.index('"ue_super90"'));old,end=json.JSONDecoder().raw_decode(text[start:]);new=copy.deepcopy(old)
keys={'false','phantom_reargrip','stable_antislip_reargrip','balanced_reargrip'}
new['options']['reargrip']=[copy.deepcopy(o) for o in source['options']['reargrip'] if o['id'] in keys]
if 'reargrip' not in new['allowed']:new['allowed'].insert(new['allowed'].index('stock'),'reargrip')
indent=len(text[text.rfind('\n',0,start)+1:start]);replacement=json.dumps(new,ensure_ascii=False,indent=2).replace('\n','\n'+' '*indent)
backup=O/'Before/gunsmith.json';backup.parent.mkdir(exist_ok=True)
if not backup.exists():backup.write_bytes(path.read_bytes())
path.write_text(text[:start]+replacement+text[start+end:],encoding='utf-8')
(O/'catalog_integration.json').write_text(json.dumps({'weapon':'ue_super90','slot':'reargrip','source_weapon':source['id'],'options':new['options']['reargrip'],'uses_existing_parts_save_schema':True,'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('SUPER90_REARGRIP_CATALOG_SAVED')
