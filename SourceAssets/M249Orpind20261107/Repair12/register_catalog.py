"""Patch only M249's optics list; retain factory-only non-optic slots."""
import copy,json,hashlib
from pathlib import Path
r=Path(__file__).resolve().parent;p=r.parents[2]/'Content/ColdSteelData/gunsmith.json'
raw=p.read_bytes();text=raw.decode('utf-8-sig');data=json.loads(text)
weapon=next(w for w in data['weapons'] if w['id']=='ue_m249')
base=next(w for w in data['weapons'] if w['id']=='ue_m24')
keys=('holographic','eoth_holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','kv_scope_4x','thermal_scope')
pool={o['id']:o for o in base['options']['optic']+data.get('common_options',{}).get('optic',[])}
before=copy.deepcopy(weapon);existing={o['id'] for o in weapon['options']['optic']}
for key in keys:
    if key not in existing:weapon['options']['optic'].append(copy.deepcopy(pool[key]))
weapon['inherit_common_options']=False
at=text.index('"id": "ue_m249"');start=text.rfind('{',0,at);_,end=json.JSONDecoder().raw_decode(text[start:]);end+=start
newline='\r\n' if '\r\n' in text[start:end] else '\n'
replacement=json.dumps(weapon,ensure_ascii=False,indent=2).replace('\n','\n    ').replace('\n',newline)
updated=text[:start]+replacement+text[end:]
if p.read_bytes()!=raw:raise RuntimeError('Catalog changed; preserve concurrent edits')
p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+updated.encode('utf-8'))
(r/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_m249','common_optics':list(keys),'factory_optic_retained':True,'other_slots_factory_only':True,'shared_icons':True,'before_entry':before,'catalog_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('M249 common optics catalog saved',len(keys))
