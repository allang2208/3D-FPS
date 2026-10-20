"""Record the completed scope without confusing scatter misses with lost hits."""
import json, re, shutil, hashlib
from pathlib import Path

O = Path(__file__).parent
source = O / 'full-60fps-02-user/Saved/SVCHFullFireReview/assertions.log'
report = source.read_text(encoding='utf-8-sig')
shutil.copyfile(source, O / 'runtime-assertions.log')
cases = []
for line in report.splitlines():
    if line.startswith('CASE '):
        row = dict(re.findall(r'(\w+)=([^ ]+)', line))
        for key in ('index', 'aim', 'kind', 'expected_target_hits', 'actual_target_hits', 'shots'):
            row[key] = int(row[key])
        row['distance_m'] = float(row['distance_m'])
        cases.append(row)
completion = re.search(r'SVCH_FULL_COMPLETE checks=(\d+) failures=(\d+)', report)
if not completion:
    raise RuntimeError('No completed runtime receipt')
receipt = {
    'status': 'completed', 'build_target': 'FPSGAMEEditor Win64 Development',
    'build_exit': 0, 'build_log': str(O / 'build-review-03.log'),
    'runtime_exit': 0, 'runtime_log': str(O / 'full-60fps-02.log'),
    'checks': int(completion[1]), 'failures': int(completion[2]),
    'case_count': len(cases), 'actual_shots': sum(row['shots'] for row in cases),
    'fixed_timestep_fps': 60, 'rendering': 'NullRHI; no screenshots',
    'isolated_profile_and_user_directory': True,
    'hip_spread_multiplier': 4.6, 'grounded_hip_tangent': 0.161,
    'hip_halfwidth_cm_at_50m': 805.,
    'hip_center_proxy_shots': sum(row['shots'] for row in cases if not row['aim'] and row['kind']==0),
    'hip_center_proxy_hits': sum(row['actual_target_hits'] for row in cases if not row['aim'] and row['kind']==0),
    'ads_center_proxy_shots': sum(row['shots'] for row in cases if row['aim'] and row['kind']==0),
    'ads_center_proxy_hits': sum(row['actual_target_hits'] for row in cases if row['aim'] and row['kind']==0),
    'real_monster_cases': 8, 'monsters': ['HandBrain', 'NurseZombie'],
    'night_warden': 'Earlier missing collision replaced in workspace during wait; current defaults confirmed QueryOnly/Visibility Block/PA_NightWardenRig. Not authored here; damage not retested.',
    'weapon_stats_changed': False, 'weapon_art_or_animation_changed': False,
    'network_runtime_tested': False,
    'binary_sha256': hashlib.sha256(Path('Binaries/Win64/UnrealEditor-FPSGAME.dll').read_bytes()).hexdigest(),
    'cases': cases
}
(O / 'delivery_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
parent = O.parent / 'delivery_receipt.json'
previous = json.loads(parent.read_text(encoding='utf-8'))
previous['full_fire_review'] = str(O / 'delivery_receipt.json')
parent.write_text(json.dumps(previous, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(f"Recorded {receipt['case_count']} cases, {receipt['actual_shots']} shots, {receipt['checks']} checks, {receipt['failures']} failures")
