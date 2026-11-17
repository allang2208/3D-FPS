"""Apply the reviewed recipe through the existing editor; caller owns the UE gate."""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/MeteorVisualReview20261114'
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
import repair_meteor_visual_scale_20261114 as repair

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert Path(u.Paths.project_content_dir()).resolve() == (ROOT / 'Content').resolve(), 'Wrong project'
assert json.loads((OUT/'Final/process.json').read_text(encoding='utf-8-sig'))['exit_code'] == 0
candidate_receipt = (OUT/'scale-repair.json').read_text(encoding='utf8')
assert json.loads(candidate_receipt)['revision'] == 3
names = ['NS_MeteorPressureV7','M_PressureCombustionV7','M_PressureAfterSmokeV7','M_PressureRaysV7','M_GroundPressureV7']
directory = ROOT/'Content/Skills/FireMagic20260921/MeteorImpactReferenceV7'
before = {}
for name in names:
    before[name] = digest(directory/(name+'.uasset'))
    assert before[name] == digest(OUT/'BeforeAssets'/(name+'.uasset')), 'Target changed since baseline: '+name
(OUT/'candidate-revision3.json').write_text(candidate_receipt, encoding='utf8')
repair.run()
receipt = dict(published_at=datetime.now().isoformat(), via='existing_editor_python_bridge', revision=3,
               assets=[dict(path=str(directory/(n+'.uasset')), before_sha256=before[n],
                            saved_sha256=digest(directory/(n+'.uasset'))) for n in names],
               visual_evidence='Final: 150 frames at 60 fps, actual UE Niagara offscreen render',
               editor_started_by_this_task=False, game_launched=False,
               preserved=['rock and fragments','V6 mantle and trail','V4 low fire','gameplay values','sound','camera'])
(OUT/'published.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
print('METEOR_REVIEW_PUBLISHED '+str(OUT/'published.json'), flush=True)
