"""Update only this weapon's no-optic description, preserving saved option IDs."""
import json
from pathlib import Path
O=Path(__file__).resolve().parent
P=O.parents[1]/'Content/ColdSteelData/gunsmith.json'
if not json.loads((O/'install_receipt.json').read_text())['complete']:
    raise RuntimeError('Mechanical sight asset has not been saved')
raw=P.read_bytes();text=raw.decode('utf-8-sig')
start=text.rfind('{',0,text.index('"id": "ue_m24"'))
weapon,end=json.JSONDecoder().raw_decode(text[start:]);end+=start
option=next(x for x in weapon['options']['optic'] if x['id']=='none')
weapon['options']['optic']=[x for x in weapon['options']['optic'] if x['id']!='m24_palma_iron']
option.update(name='M24 觇孔机械瞄具',description='取下光学瞄准镜，使用侧置调节座、觇孔照门与护筒准星组成的机械瞄具总成。',
              special_effects=['机械瞄准｜使用觇孔照门与前准星，不提供光学放大。'])
lines=json.dumps(weapon,ensure_ascii=False,indent=2).splitlines()
replacement=lines[0]+'\n'+'\n'.join('    '+x for x in lines[1:])
backup=O/'before_gunsmith.json'
if not backup.exists():backup.write_bytes(raw)
if P.read_bytes()!=raw:raise RuntimeError('Catalog changed concurrently; rerun this registration')
P.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+(text[:start]+replacement+text[end:]).encode('utf-8'))
(O/'registration_receipt.json').write_text(json.dumps({'weapon':'ue_m24','no_optic_visual':'m24_palma_iron','preserved_ids':True,'runtime_tested':False},indent=2))
print('M24_NO_OPTIC_CATALOG_REGISTERED')
