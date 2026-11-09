"""Publish faster magazine reload stats through the existing benefit rows."""
import json,copy,hashlib
from pathlib import Path
r=Path(__file__).resolve().parent;p=r.parents[2]/'Content/ColdSteelData/gunsmith.json'
if not json.loads((r/'install_receipt.json').read_text()).get('complete'):raise RuntimeError('Save actions and icon before publishing stats')
raw=p.read_bytes();text=raw.decode('utf-8-sig');data=json.loads(text);w=next(w for w in data['weapons'] if w['id']=='ue_m249');before=copy.deepcopy(w);updated=[]
for key,normal,empty in [('m249_side_mag_30',3.6,4.8),('m249_side_mag_45',3.9,5.1)]:
    o=next(o for o in w['options']['magazine'] if o['id']==key)
    o['stats']['reload_mult']=normal/w['base']['reload_time'];o['stats']['empty_reload_mult']=empty/w['base']['empty_reload_time']
    o['special_effects']=['侧插供弹｜左手抓牢并拔出旧弹匣，再取新匣从侧面插入、压实；机匣盖保持关闭，空仓装填后拉栓。']
    # SelectedDetails and Overview derive both duration benefit rows from these
    # actual multipliers; do not duplicate the numbers in descriptive text.
    updated.append(dict(id=key,normal_seconds=normal,empty_seconds=empty,reload_mult=o['stats']['reload_mult'],empty_reload_mult=o['stats']['empty_reload_mult']))
at=text.index('"id": "ue_m249"');start=text.rfind('{',0,at);_,n=json.JSONDecoder().raw_decode(text[start:]);end=start+n;nl='\r\n' if '\r\n' in text[start:end] else '\n'
replacement=json.dumps(w,ensure_ascii=False,indent=2).replace('\n','\n    ').replace('\n',nl)
if p.read_bytes()!=raw:raise RuntimeError('Concurrent catalog edit retained')
if not (r/'catalog_before.json').exists():(r/'catalog_before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2),encoding='utf8')
p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+(text[:start]+replacement+text[end:]).encode('utf8'))
(r/'catalog_receipt.json').write_text(json.dumps(dict(weapon='ue_m249',updated=updated,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),runtime_tested=False),indent=2))
print('M249_SIDE_MAG_RELOAD_BENEFITS_PUBLISHED')
