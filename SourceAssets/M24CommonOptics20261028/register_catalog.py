"""Patch only the current M24 catalog entry; keep parallel catalog work intact."""
import copy,json
from pathlib import Path
O=Path(__file__).resolve().parent
p=O.parents[1]/'Content/ColdSteelData/gunsmith.json'
raw=p.read_bytes();text=raw.decode('utf-8-sig');data=json.loads(text)
m24=next(w for w in data['weapons'] if w['id']=='ue_m24')
base=next(w for w in data['weapons'] if w['id']=='ue_m4a1')
existing={o['id'] for o in m24['options']['optic']}
keys=('holographic','eoth_holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','kv_scope_4x','thermal_scope')
pool={o['id']:o for o in base['options']['optic']+data['common_options']['optic']}
backup=O/'before_m24_catalog.json'
if not backup.exists():backup.write_text(json.dumps(m24,ensure_ascii=False,indent=2),encoding='utf-8')
for key in keys:
    if key not in existing:m24['options']['optic'].append(copy.deepcopy(pool[key]))
for trait in m24['traits']:
    if '六倍镜与机械瞄具可互换' in trait['text']:
        trait['text']='原厂六倍镜、机械瞄具与通用光学瞄具可互换；消音器和贴腮板可独立拆装，新枪默认采用原装组合。'
# Preserve M24's opt-out from unrelated common tactical slots. Its supported
# thermal optic is copied explicitly alongside the six existing rifle options.
at=text.index('"id": "ue_m24"');start=text.rfind('{',0,at)
old,end=json.JSONDecoder().raw_decode(text[start:]);end+=start
newline='\r\n' if '\r\n' in text[start:end] else '\n'
replacement=json.dumps(m24,ensure_ascii=False,indent=2).replace('\n','\n    ').replace('\n',newline)
updated=text[:start]+replacement+text[end:]
if p.read_bytes()!=raw:raise RuntimeError('Catalog changed during this patch; retained newer data')
p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+updated.encode('utf-8'))
(O/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_m24','added_common_optics':list(keys),'shared_icons':True,'runtime_tested':False},indent=2),encoding='utf-8')
print('M24_COMMON_OPTIC_CATALOG_REGISTERED',len(keys))
