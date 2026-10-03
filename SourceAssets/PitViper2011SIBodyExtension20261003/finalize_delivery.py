"""Record actual saved SI body-extension mesh and its production card icon."""
import json
from pathlib import Path
O=Path(__file__).parent;SI=O.parent/'PitViper2011SICompensator20261002'
mesh=json.loads((O/'import_receipt.json').read_text(encoding='utf8'))
icon=json.loads((SI/'icon_delivery.json').read_text(encoding='utf8'))
author=json.loads((O/'authoring_receipt.json').read_text(encoding='utf8'))
if mesh.get('status')!='imported_and_saved' or icon.get('status')!='imported_and_saved':
    raise RuntimeError('The production assets have not both been saved')
delivery={'status':'remodeled_imported_and_saved','part':'pit_viper_si_compensator','date':'2026-10-03',
    'revision':'actual native side-view muzzle rake and uniform-width body extension',
    'model':mesh,'author':author,'icon':icon,'native_build_required':False,
    'game_tested':False,'acceptance_rendered':False,'editor_opened':False}
(O/'delivery_receipt.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf8')
path=SI/'delivery_receipt.json';prior=json.loads(path.read_text(encoding='utf8'))
prior['latest_interface_revision']=delivery
path.write_text(json.dumps(prior,ensure_ascii=False,indent=2),encoding='utf8')
(O/'icon_delivery.json').write_text(json.dumps(icon,ensure_ascii=False,indent=2),encoding='utf8')
print('SI_BODY_EXTENSION_MESH_AND_ICON_SAVED',flush=True)
