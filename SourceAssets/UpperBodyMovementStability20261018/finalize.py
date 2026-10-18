import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

task = Path(__file__).resolve().parent
root = task.parents[1]
def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))
comparison = read(task / 'comparison.json')
contact = read(task / 'contact-receipt.json')
cases = read(Path(contact['directory']) / 'result.json')
if not comparison['passed'] or contact['exit_code'] != 0 or cases['failed'] != 0 or cases['cases'] != 45:
    raise RuntimeError('Required movement/contact diagnosis is incomplete.')
builds = {}
for target in ('Editor', 'Game'):
    path = sorted(task.glob(f'Build-*-{target}'))[-1] / 'result.json'
    if read(path)['build'] != 'Succeeded':
        raise RuntimeError(f'{target} build incomplete.')
    builds[target] = path.relative_to(root).as_posix()
files = [
    'Source/FPSGAME/Characters/FPSBodyBowPose.inl',
    'Source/FPSGAME/Characters/FPSBodyConsumePose.inl',
    'Source/FPSGAME/Characters/FPSUpperBodyContinuityDiagnosis.cpp',
    'Source/FPSGAME/Characters/BowSparrowPresentationAudit.cpp',
    'Source/FPSGAME/Skills/BowSkillTrainingAuditCommandlet.cpp',
    'Source/FPSGAME/Development/HumanoidHitVolumeAuthoringCommandlet.cpp',
]
result = {
    'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
    'status': 'built_and_numeric_diagnosis_complete',
    'request': 'Fix upper-body shaking while moving with a bow, eating or drinking, observed on the local third-person body.',
    'cause': 'Native local spine poses were attached to the unrelated moving gait pelvis without preserving the authored chest frame. Gait pelvis yaw/roll therefore propagated into the action torso and both arms.',
    'fix': 'Anchor the authored chest orientation in mesh component space at the live pelvis position. Bow aiming follows that anchor; consumption mouth/prop correction follows the anchored torso. Existing blend weights, source action clocks and hand/finger tracks remain in use.',
    'source_sha256': {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in files},
    'comparison': comparison,
    'contact': {'receipt': contact, 'cases': cases['cases'], 'failed': cases['failed'],
                'moving_cases': [r for r in cases['results'] if r['case'].startswith('moving ')]},
    'builds': builds,
    'build_unblock': 'Three mechanical C++ type fixes in HumanoidHitVolumeAuthoringCommandlet.cpp: two explicit TObjectPtr.Get() calls and a signed triangle-loop bound. Its authoring behavior was not exercised here.',
    'assets_reauthored': False,
    'limits': [
        '48 graph-isolation cases use live locomotion with fixed action poses, not a rendered gameplay capture or full consumable transaction.',
        '45 component assertions include nine moving bow contact cases; this is not a new socket/Internet test.',
        'Ground traces, visual skin/clothing acceptance and actual player movement input remain for in-game confirmation.',
    ],
    'gui_editor_launched': False,
}
(task / 'delivery.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'cases': comparison['cases'], 'contact_cases': cases['cases'], 'builds': builds}))
