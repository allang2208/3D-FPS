"""Publish only M249's magazine options after the real asset save finishes."""
import json,copy,hashlib
from pathlib import Path
r=Path(__file__).resolve().parent;p=r.parents[2]/'Content/ColdSteelData/gunsmith.json'
if not json.loads((r/'install_receipt.json').read_text()).get('complete'):raise RuntimeError('Assets must be saved before catalog publication')
raw=p.read_bytes();text=raw.decode('utf-8-sig');data=json.loads(text);w=next(w for w in data['weapons'] if w['id']=='ue_m249');before=copy.deepcopy(w)
specs=[('m249_side_mag_30','30发侧插弹匣',30,4.1,5.3),('m249_side_mag_45','45发扩容侧插弹匣',45,4.4,5.6)]
for key,name,rounds,normal,empty in specs:
    option=dict(id=key,name=name,description='弧形防滑匣体与独立金属插口，沿机匣左侧接入。' if rounds==30 else '沿原有曲线延长匣体，保留上部插接段与防滑纹路。',effects=[],stats=dict(mag_delta=rounds-int(w['base']['mag_size']),reload_mult=normal/w['base']['reload_time'],empty_reload_mult=empty/w['base']['empty_reload_time']),special_effects=['侧插供弹｜替换弹箱与弹链，换弹时保持机匣盖关闭；空仓装填后拉栓。'])
    index=next((i for i,o in enumerate(w['options']['magazine']) if o['id']==key),None)
    if index is None:w['options']['magazine'].append(option)
    else:w['options']['magazine'][index]=option
at=text.index('"id": "ue_m249"');start=text.rfind('{',0,at);_,length=json.JSONDecoder().raw_decode(text[start:]);end=start+length
newline='\r\n' if '\r\n' in text[start:end] else '\n';replacement=json.dumps(w,ensure_ascii=False,indent=2).replace('\n','\n    ').replace('\n',newline)
if p.read_bytes()!=raw:raise RuntimeError('Concurrent catalog edit retained')
if not (r/'catalog_before.json').exists():(r/'catalog_before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2),encoding='utf8')
p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+(text[:start]+replacement+text[end:]).encode('utf8'))
(r/'catalog_receipt.json').write_text(json.dumps(dict(weapon='ue_m249',options=[s[0] for s in specs],capacity=[30,45],normal_seconds=[4.1,4.4],empty_seconds=[5.3,5.6],sha256=hashlib.sha256(p.read_bytes()).hexdigest(),runtime_tested=False),indent=2))
print('M249_SIDE_MAG_CATALOG_SAVED')
