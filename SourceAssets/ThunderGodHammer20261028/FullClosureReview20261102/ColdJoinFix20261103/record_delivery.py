from pathlib import Path
from datetime import datetime
import json

OUT = Path(__file__).parent
read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
build = read(OUT / 'build-receipt.json')
if not build['compiled'] or not build['owned_sources_unchanged_during_build']:
    raise SystemExit('Final build must cover unchanged owned sources.')
delivery = {
    'date': datetime.now().astimezone().isoformat(),
    'implemented': True,
    'compiled': True,
    'build': build,
    'runtime_tested': False,
    'status': 'implemented_and_built_awaiting_user_visual_test',
    'scope': 'Initial world-body appearance waits for selected head assembly and its first finalized bone pose. Existing complete appearance remains while switching. No weapon gameplay/network protocol changes.',
    'readiness': 'Per-instance render state started only in game BeginPlay, not constructor/previews/dedicated server. Body/head bones continue updating while hidden.',
    'failure_behavior': 'Invalid/missing catalog assets retain diagnostics and release the initial display gate to avoid permanently invisible players; asset repair is outside this change.',
}
(OUT / 'delivery.json').write_text(json.dumps(delivery, ensure_ascii=False, indent=2), encoding='utf-8')
print('Cold-join fix implemented and built; runtime verification remains with the user.')
