"""Enable the four requested shared slots while retaining the original options."""
import copy,json,hashlib
from pathlib import Path
r=Path(__file__).resolve().parent;p=r.parents[2]/'Content/ColdSteelData/gunsmith.json'
receipt=json.loads((r/'install_receipt.json').read_text())
if not receipt.get('complete'):raise RuntimeError('Save the actual assets before enabling the options')
raw=p.read_bytes();text=raw.decode('utf-8-sig');data=json.loads(text)
weapon=next(w for w in data['weapons'] if w['id']=='ue_m249');donor=next(w for w in data['weapons'] if w['id']=='ue_lmg201');before=copy.deepcopy(weapon)
slots=('muzzle','stock','reargrip','underbarrel');added={}
for slot in slots:
    present={o['id'] for o in weapon['options'][slot]};added[slot]=[]
    for option in donor['options'][slot]:
        if option['id']=='false' or option['id'] in present:continue
        weapon['options'][slot].append(copy.deepcopy(option));added[slot].append(option['id']);present.add(option['id'])
weapon['inherit_common_options']=False
at=text.index('"id": "ue_m249"');start=text.rfind('{',0,at);_,end=json.JSONDecoder().raw_decode(text[start:]);end+=start
newline='\r\n' if '\r\n' in text[start:end] else '\n'
replacement=json.dumps(weapon,ensure_ascii=False,indent=2).replace('\n','\n    ').replace('\n',newline)
updated=text[:start]+replacement+text[end:]
if p.read_bytes()!=raw:raise RuntimeError('Catalog changed; preserve concurrent edits')
p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+updated.encode('utf-8'))
(r/'catalog_receipt.json').write_text(json.dumps(dict(weapon='ue_m249',added=added,source='ue_lmg201 common options',before_entry=before,shared_icons=True,catalog_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('M249 common parts catalog saved',sum(len(a) for a in added.values()))
