"""Record the current R5 production receipt without loading assets or running tests."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
current=P/'ContinuousBladesR5_20261104'
data=json.loads((current/'delivery.json').read_text('utf-8'))
if not data['complete']:raise RuntimeError('R5 production is not finished')
data.update({'date':'2026-11-04','definition':'ue_tactical_hatchet','status':'imported_saved_and_registered',
    'current_source_directory':str(current),'current_import_receipt':str(current/'import_receipt.json'),
    'retained_crescent_geometry':'CrescentReferenceR4_20261104/SwiftCrescent_Editable.blend',
    'factory_and_grip_pommel_retained':True,'native_code_changed':False,'native_build_required':False,
    'editor_ui_started':False,'gameplay_tested':False,'acceptance_rendered':False})
(P/'delivery.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('HATCHET_R5_DELIVERED models=2 icons=3 saved_assets='+str(data['ue_saved_asset_count']))
