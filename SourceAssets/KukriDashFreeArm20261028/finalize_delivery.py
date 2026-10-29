import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
OUT = Path(__file__).resolve().parent
def read(name): return json.loads((OUT / name).read_text(encoding='utf-8-sig'))
saved, published = read('assets-saved.json'), read('published.json')
if not saved['complete'] or not published['local_configuration']:
    raise RuntimeError('Saving or configuration publication is incomplete')
receipt = dict(completed=datetime.now(timezone(timedelta(hours=8))).isoformat(),
    scope='Single third-person dash left arm only, Jason and Kaitlin',
    assets=saved, publication=published, diagnosis=read('diagnosis.json'), saved_comparison=read('saved-comparison.json'),
    cpp_changed=False, build_required=False, first_person_changed=False, dual_changed=False,
    runtime_tested=False, game_started=False, rendered=False, visual_acceptance='User pending',
    documentation='Docs/Weapons/kukri-dash-single-free-arm-20261028.md')
(OUT / 'delivery.json').write_text(json.dumps(receipt, indent=2))
print('SINGLE_DASH_FREE_ARM_DELIVERED')
