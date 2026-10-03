"""Record saved production outputs; does not run game checks or acceptance."""
import json
from pathlib import Path

O=Path(__file__).parent
integration=json.loads((O/'integration_receipt.json').read_text(encoding='utf8'))
build=json.loads((O/'build_receipt.json').read_text(encoding='utf-8-sig'))
icon=json.loads((O/'icon_delivery.json').read_text(encoding='utf8'))
catalog=json.loads((O/'catalog.json').read_text(encoding='utf8'))
if integration.get('status')!='imported_and_saved' or not integration.get('catalog_published'):
    raise RuntimeError('Production model and catalog are not saved yet')
if build.get('status')!='Succeeded' or icon.get('status')!='imported_and_saved':
    raise RuntimeError('Production binaries and icon are not saved yet')
integration.update(native_code_required=False,native_code_built=True,delivery_status='integrated_and_built')
(O/'integration_receipt.json').write_text(json.dumps(integration,ensure_ascii=False,indent=2),encoding='utf8')
delivery={'status':'integrated_and_built','date':'2026-10-03','weapon':'ue_pit_viper2011',
          'part':'pit_viper_si_compensator','ui_path':'2011 → 改造 → 枪口 → SI 枪口补偿器（限定）',
          'saved_assets':integration['saved'],'native_families':integration['families'],
          'catalog':catalog,'icon':icon,'build':build,
          'game_tested':False,'acceptance_rendered':False,'gui_editor_launched':False}
(O/'delivery_receipt.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf8')
print('PIT_VIPER_SI_COMPENSATOR_INTEGRATED_AND_BUILT',flush=True)
