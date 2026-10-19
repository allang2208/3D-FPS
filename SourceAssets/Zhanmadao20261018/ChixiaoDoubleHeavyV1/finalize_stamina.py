import json
from datetime import datetime
from pathlib import Path

P = Path(__file__).resolve().parent
builds = [json.loads((P / f'build-{target}-receipt-stamina-01.json').read_text('utf-8-sig'))
          for target in ('FPSGAMEEditor', 'FPSGAME')]
if any(build['exit_code'] != 0 for build in builds):
    raise RuntimeError('Stamina build unfinished')

receipt = json.loads((P / 'delivery.json').read_text('utf-8-sig'))
receipt.update(
    charge_and_stamina='one_original_charge_double_release_cost',
    release_stamina_multiplier=2,
    stamina_updated_at=datetime.now().astimezone().isoformat(),
    native_builds=builds,
    runtime_tested=False,
)
(P / 'delivery.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('CHIXIAO_DOUBLE_RELEASE_STAMINA_SAVED', flush=True)
