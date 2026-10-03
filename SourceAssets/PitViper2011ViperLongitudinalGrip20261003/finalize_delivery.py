"""Record the successful production save, without running acceptance checks."""
import json
from pathlib import Path
O=Path(__file__).parent
receipt=json.loads((O/'import_receipt.json').read_text(encoding='utf8'))
auth=json.loads((O/'authoring.json').read_text(encoding='utf8'))
delivery={'status':receipt['status'],'part':'pit_viper_vip_scales','revision':auth['revision'],
    'change':'longitudinal skins on both grip-body sides; native slanted bottom seam; exclude magazine, baseplate and magwell',
    'authoring':str(O/'authoring.json'),'blend':auth['blend'],'fbx':auth['fbx'],
    'saved':receipt['saved'],'icon':receipt['icon'],
    'hip_spread_mult':.85,'si_stats_changed':False,'shared_grips_changed':False,
    'native_build_required':False,'game_tested':False,'acceptance_rendered':False,
    'production_save_receipt':str(O/'import_receipt.json')}
(O/'delivery_receipt.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf8')
print('VIP_LONGITUDINAL_GRIP_DELIVERY_SAVED',flush=True)
