"""Expose saved Super90 grips through the existing gunsmith/save pipeline."""
import json,copy,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];B=O/'Before';B.mkdir(exist_ok=True)
receipt=json.loads((O/'import_receipt.json').read_text())
if not receipt.get('completed'):raise RuntimeError('Foregrip asset save is incomplete')
file=P/'Content/ColdSteelData/gunsmith.json'
if not (B/file.name).exists():shutil.copy2(file,B/file.name)
catalog=json.loads(file.read_text(encoding='utf-8-sig'));target=next(w for w in catalog['weapons'] if w['id']=='ue_super90')
source=next(w for w in catalog['weapons'] if w['id']=='ue_hk416')
ids=('vertical_foregrip','tactical_vertical_foregrip','canted_foregrip','prism_handstop','angled_foregrip')
factory=next(o for o in target['options']['underbarrel'] if o['id']=='false')
target['options']['underbarrel']=[factory]+copy.deepcopy([o for o in source['options']['underbarrel'] if o['id'] in ids])
for row in target['options']['underbarrel'][1:]:
    row['description']=row.get('description','').replace('HK416','Super90').replace('M4A1','Super90')
file.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(O/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_super90','options':[o['id'] for o in target['options']['underbarrel']],
    'save_path':'Existing gunsmith_parts item data and Normalize/Installed/Apply pipeline','runtime_tested':False},indent=2))
print('SUPER90_FOREGRIPS_CATALOG_SAVED',len(target['options']['underbarrel'])-1)
