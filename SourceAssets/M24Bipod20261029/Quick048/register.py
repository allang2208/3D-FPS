"""Consolidate only M24's duplicate iron-sight option; retain the standard none ID."""
import json
from pathlib import Path
O=Path(__file__).resolve().parent
P=O.parents[2]/'Content/ColdSteelData/gunsmith.json'
raw=P.read_bytes();text=raw.decode('utf-8-sig')
start=text.rfind('{',0,text.index('"id": "ue_m24"'))
weapon,end=json.JSONDecoder().raw_decode(text[start:]);end+=start
opts=weapon['options']['optic']
none=next(x for x in opts if x['id']=='none')
none.update(name='M24 觇孔机械瞄具',description='取下光学瞄准镜，使用侧置调节座、觇孔照门与护筒准星组成的机械瞄具总成。',
            special_effects=['机械瞄准｜使用觇孔照门与前准星，不提供光学放大。'])
weapon['options']['optic']=[x for x in opts if x['id']!='m24_palma_iron']
lines=json.dumps(weapon,ensure_ascii=False,indent=2).splitlines()
replacement=lines[0]+'\n'+'\n'.join('    '+x for x in lines[1:])
if P.read_bytes()!=raw:raise RuntimeError('M24 catalog changed concurrently; registration not written')
P.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+(text[:start]+replacement+text[end:]).encode('utf-8'))
(O/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_m24','retained_id':'none','legacy_alias':'m24_palma_iron',
    'saved':str(P),'runtime_tested':False},indent=2),encoding='utf-8')
print('M24_IRON_SIGHT_OPTION_CONSOLIDATED')
