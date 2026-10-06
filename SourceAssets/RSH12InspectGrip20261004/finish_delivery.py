"""Record completed authoring/import/build stages without starting the game."""
import json,hashlib
from pathlib import Path
O=Path(__file__).parent;previous=O.parent/'RSH12Speedloader20261003'
saved=json.loads((O/'import_receipt.json').read_text())
build=json.loads((previous/'build_receipt.json').read_text(encoding='utf-8-sig'))
diagnosis=json.loads((O/'diagnosis_single_after.json').read_text())['r']
maximum=max(v['deepest_mm'] for e in diagnosis for v in e['contact'].values())
result=dict(status='saved',revision=saved['revision'],saved=saved['saved'],runtime_tested=False,
    scope='Single RSH12 right-hand grasp and inspect; shared 715 action and speedloader retained',
    base_editor_build=build['status'],new_cpp_changes=False,
    profile_sha256=hashlib.sha256((O/'Single/profile.json').read_bytes()).hexdigest(),
    requested_offline_diagnosis=dict(sampled_poses=len(diagnosis),full_mixed_weight_hand_vertices=6052,max_sampled_grip_penetration_mm=maximum),
    editor_ui_started=False,game_started=False)
(O/'delivery.json').write_text(json.dumps(result,indent=2),encoding='utf8')
status=json.loads((previous/'delivery.json').read_text())
status.update(status='assets_saved_build_succeeded',build_required=False,build_result=build['status'],single_grip_successor='RSH12InspectGrip20261004')
status.pop('blocker',None)
(previous/'delivery.json').write_text(json.dumps(status,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False))
