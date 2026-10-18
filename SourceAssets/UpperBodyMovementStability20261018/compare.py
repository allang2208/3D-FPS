import json
from pathlib import Path
import numpy as np

task = Path(__file__).resolve().parent
def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))
receipts = {phase: read(task / f'{phase}-receipt.json') for phase in ('before', 'after')}
if any(r['exit_code'] != 0 for r in receipts.values()):
    raise RuntimeError('A diagnosis did not exit normally.')
data = {phase: read(Path(r['directory']) / 'poses.json') for phase, r in receipts.items()}
def key(c):
    return c['action'], c['speed'], c['direction'], c['post_process']
before = {key(c): np.asarray(c['samples'], dtype=float) for c in data['before']['cases']}
after = {key(c): np.asarray(c['samples'], dtype=float) for c in data['after']['cases']}
if before.keys() != after.keys():
    raise RuntimeError('Before/after case matrices differ.')
bones = data['after']['bones']
pelvis = bones.index('pelvis')
chest = bones.index('spine_03')
head = bones.index('head')
pelvis_error = max(float(np.abs(after[k][:, pelvis] - v[:, pelvis]).max()) for k, v in before.items())
base_error = max(float(np.abs(after[k] - v).max()) for k, v in before.items() if k[0] == 'base')
def angle(a, b):
    a = a / np.linalg.norm(a, axis=-1, keepdims=True)
    b = b / np.linalg.norm(b, axis=-1, keepdims=True)
    return np.rad2deg(2 * np.arccos(np.clip(np.abs(np.sum(a * b, axis=-1)), 0, 1)))
rotation_error = max(float(angle(v[:, chest, 3:], after[(k[0], 0, 0, k[3])][:, chest, 3:]).max())
                     for k, v in after.items() if k[0] != 'base' and k[1] > 0)
post_error = max(float(np.abs(v - after[(k[0], k[1], k[2], False)]).max())
                 for k, v in after.items() if k[3])
checks = {
    'base_graph_unchanged': base_error < 1e-5,
    'pelvis_unchanged_all_cases': pelvis_error < 1e-5,
    'moving_upper_orientation_matches_same_authored_frame_at_rest': rotation_error < .01,
    'all_output_finite': all(np.isfinite(v).all() for v in after.values()),
}
strafe = ('bow_hold', 240, 90, True)
run = ('bow_hold', 480, 0, True)
result = {
    'cases': len(after), 'frames_per_case': 300, 'fps': 60,
    'checks': checks, 'passed': all(checks.values()),
    'base_pose_max_element_error': base_error,
    'pelvis_max_element_error': pelvis_error,
    'upper_rotation_moving_vs_stationary_max_degrees': rotation_error,
    'post_process_main_bone_max_element_difference': post_error,
    'bow_hold_strafe_head_fore_aft_range_cm': {p: float(np.ptp(d[strafe][:, head, 1])) for p, d in (('before', before), ('after', after))},
    'bow_hold_run_chest_max_adjacent_rotation_degrees': {p: float(angle(d[run][1:, chest, 3:], d[run][:-1, chest, 3:]).max()) for p, d in (('before', before), ('after', after))},
    'receipts': receipts,
    'limits': ['Native graph isolation with live gait and fixed action pose.', 'No ground traces, prop-to-mouth IK, gameplay input, rendering or network transport in this matrix.'],
}
(task / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in result.items() if k not in ('receipts', 'limits')}, indent=2))
if not result['passed']:
    raise RuntimeError('Continuity isolation checks failed.')
