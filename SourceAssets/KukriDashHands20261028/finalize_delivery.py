"""Record completed build, saved sequences and scoped route installation."""
import json
from pathlib import Path
from datetime import datetime,timezone,timedelta
OUT=Path(__file__).resolve().parent
def read(name):return json.loads((OUT/name).read_text(encoding='utf-8-sig'))
saved,published=read('assets-saved.json'),read('published.json')
build,commandlet=read('editor-build-resume-result.json'),read('save_all-commandlet.json')
if not saved.get('complete') or not published.get('local_configuration') or build['exit_code'] or commandlet['exit_code']:
    raise RuntimeError('Required production stage remains incomplete')
result=dict(completed=datetime.now(timezone(timedelta(hours=8))).isoformat(),
    scope='Single natural free arm and dedicated dual-blade third-person sprint overhead',
    assets_saved=True,saved_assets=saved['bodies'],publication=published,build=build,save_commandlet=commandlet,
    cpp_changed=['Source/FPSGAME/Characters/FPSBodyKukriMotion.h','Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.cpp'],
    first_person_changed=False,gameplay_movement_changed=False,game_run=False,runtime_tested=False,rendered=False,
    visual_acceptance='User pending',documentation='Docs/Weapons/kukri-dash-single-dual-hands-20261028.md')
(OUT/'delivery.json').write_text(json.dumps(result,indent=2))
print('KUKRI_DASH_HANDS_DELIVERED')
