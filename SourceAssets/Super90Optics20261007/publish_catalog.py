"""Expose saved common optics through the existing instance/save pipeline."""
import json,copy,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
receipt=json.loads((O/'import_receipt.json').read_text())
if not receipt.get('completed'):raise RuntimeError('Optic asset save is incomplete')
file=P/'Content/ColdSteelData/gunsmith.json';before=O/'Before/gunsmith.json'
if not before.exists():shutil.copy2(file,before)
catalog=json.loads(file.read_text(encoding='utf-8-sig'));target=next(w for w in catalog['weapons'] if w['id']=='ue_super90')
source=next(w for w in catalog['weapons'] if w['id']=='ue_hk416')
factory=next(o for o in target['options']['optic'] if o['id']=='false')
target['options']['optic']=[factory]+copy.deepcopy([o for o in source['options']['optic'] if o['id'] in ('holographic','eoth_holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x')])
for row in target.get('traits',[]):
    if row.get('text')=='保留原厂机械分件，本次目录提供原厂配置':row['text']='机匣导轨支持通用光学瞄具；装镜时收起原厂鬼环与准星'
file.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(O/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_super90','options':[o['id'] for o in target['options']['optic']],
    'save_path':'Existing gunsmith_parts item data and Normalize/Installed/Apply pipeline','runtime_tested':False},indent=2))
print('SUPER90_OPTICS_CATALOG_SAVED',len(target['options']['optic'])-1)
