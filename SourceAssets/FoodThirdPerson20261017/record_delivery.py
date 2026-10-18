"""Record actual builds and scoped checks; do not equate offline poses with game acceptance."""
import json,hashlib
from pathlib import Path
O=Path(__file__).parent;R=O.parents[1]
comparison=json.loads((O/'final_graph_comparison_final.json').read_text())
thumb=json.loads((O/'thumb_skin_final.json').read_text())
geometry=json.loads((O/'geometry_final.json').read_text())
previous_geometry=json.loads((O/'geometry_after.json').read_text())
def latest(kind):
    paths=sorted(O.glob(f'Build-*-{kind}/result.json'))
    return {'receipt':str(paths[-1].relative_to(R)),**json.loads(paths[-1].read_text(encoding='utf-8-sig'))}
files=['Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.cpp','Source/FPSGAME/Characters/FPSBodyConsumePose.inl','Source/FPSGAME/Characters/FPSFoodPoseDiagnosis.cpp']
report={'scope':'Six third-person foods on bare Jason body; explicit background final graph and skin inspection. No game, PIE or network acceptance.',
 'builds':{kind:latest(kind) for kind in ['Editor','Game']},'source_sha256':{p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in files},
 'food_results':comparison,'thumb_results':[{**{k:r[k] for k in ['food','case']},'max_folded_triangles':{s:d['worst'][1] for s,d in r['sides'].items()}} for r in thumb],
 'active_arm_torso_crossings':[{**{k:r[k] for k in ['food','case']},'counts':r['max_arm_torso_crossings']} for r in geometry+ [v for v in previous_geometry if v['food']=='roasted_large_lamb']],
 'animation_assets_changed':False,'first_person_changed':False,'game_or_pie_started':False,'visual_acceptance':'user pending',
 'known_limit':'Simplified rifle/staff inputs retain elbow folds at low consume weight and omit the full live weapon contact tables; these do not establish actual equipped-state acceptance. Single-hand probes only supply the consuming hand. Independent head/clothing surfaces and remote-client state were not inspected.'}
(O/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('FOOD_THIRD_PERSON_DELIVERED',len(comparison),'cases; Editor/Game builds recorded')
