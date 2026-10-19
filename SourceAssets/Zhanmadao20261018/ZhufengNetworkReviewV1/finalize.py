"""Record the scoped network review and its actual isolated/native build results."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
builds={}
for target in ['FPSGAMEEditor','FPSGAME']:
    paths=sorted(P.glob(f'build-{target}-*-receipt.json'))
    builds[target]=json.loads(paths[-1].read_text(encoding='utf-8-sig')) if paths else {'exit_code':None}
audits=sorted(P.glob('authority-result-*.json'))
audit=json.loads(audits[-1].read_text(encoding='utf-8-sig')) if audits else None
report={
    'revision':'ZhufengNetworkReviewV1','builds':builds,
    'catalog_checks':json.loads((P/'catalog-review.json').read_text(encoding='utf-8')),
    'native_build_complete':all(v['exit_code']==0 for v in builds.values()),
    'isolated_authority_checks':audit,
    'real_network_transport_tested':False,'visual_tested':False,'interactive_editor_started':False,
    'headless_commandlet_ran':audit is not None,
    'findings':[
        {'area':'cast commit','before':'Sword whirlwind committed cost/cooldown on the owner only; no cast-specific authority receipt.',
         'fix':'Ordered authority start/finish, cumulative stamina receipt, authoritative cooldown and invalid-state rejection.'},
        {'area':'AOE hits','before':'Ordinary per-hit firearm token bucket could reject crowded AOE; server had no cast target set.',
         'fix':'Committed cast serial, one hit per target, shared damage/range snapshot; no per-target firearm budget.'},
        {'area':'occlusion','before':'A retained gun projectile speed could classify whirlwind contacts as projectiles and skip wall checks.',
         'fix':'Whirlwind always follows melee area exposure checks.'},
        {'area':'secondary effects and training','before':'Whirlwind stun/knockback/training lived after client damage forwarding returned zero.',
         'fix':'Server confirms stun/knockback, rune effects and dash/whirlwind training once.'},
        {'area':'movement','before':'Forward move budget did not require an accepted whirlwind cast.',
         'fix':'Match move sequence to accepted cast; fixed direction, elapsed-time cap, authority movement lock, pending-channel retry.'},
        {'area':'item lifetime','before':'Local whirlwind read the inventory item after CommitState replaced the profile.',
         'fix':'Capture needed weapon identity before commit; authority retains a cast item copy.'}],
    'review_matrix':{
        'zhufeng_bonus_range_physical':'catalog/parser/aggregation/shared evaluation and isolated checks',
        'chixiao_physical_speed':'unchanged catalog and isolated evaluator checks',
        'cyan_trail':'published material, rune-free blade endpoints and body serialization',
        'third_person_motion':'existing start/loop/end and spine rotation retained; forward yaw compensation remains',
        'cast_cost_cooldown':'new authority path and upload/mirror protection',
        'AOE_dedup_and_target_count':'isolated ten-target server hit flow',
        'forward_movement':'isolated ordering/duplicate/direction checks; live latency not measured',
        'unequip_death_cancel':'authority cast closes and payments remain idempotent; disconnect/travel settle before save',
        'real_peer_render_and_transport':'not exercised'}}
(P/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ZHUFENG_NETWORK_REVIEW_SAVED')
