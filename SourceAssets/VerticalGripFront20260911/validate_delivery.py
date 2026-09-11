"""Verify final local delivery and define the exact public author-workflow file set."""
import ast
import hashlib
import json
import re
from pathlib import Path

O = Path(__file__).resolve().parent
P = O.parents[1]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


acceptance = read(O / 'opposed_acceptance.json')
assert acceptance['animation_assets_passed'] == 18
assert len(acceptance['runtime']) == 2 and not any(x['failures'] for x in acceptance['runtime'].values())
assert sum(x['samples'] for x in acceptance['geometry'].values()) == 1375
assert all(not x['finger_grip_intersection_samples'] for x in acceptance['geometry'].values())
assert all(not x.get('new_only_parts_at_sample') for x in acceptance['thumb_gun'].values())
for row in read(O / 'opposed_delivery_manifest.json'):
    path = O / row['path']
    assert path.stat().st_size == row['bytes']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256']
for row in read(O / 'reference_workflow_manifest.json'):
    assert hashlib.sha256((O / row['path']).read_text(encoding='utf-8').encode('utf-8')).hexdigest() == row['sha256_lf']
for target in re.findall(r'\]\(([^)]+)\)', (O / 'README.md').read_text(encoding='utf-8')):
    assert (O / target).is_file(), target
for path in O.glob('*.py'):
    ast.parse(path.read_text(encoding='utf-8-sig'), str(path))
for name in ['grip-arm-refinement.md', 'vertical-front-grasp.md']:
    local = P / 'skills/ue5-fps-arms-animation/references' / name
    personal = Path('C:/Users/allan/.codex/skills/ue5-fps-arms-animation/references') / name
    assert local.read_bytes() == personal.read_bytes()

files = [
    'README.md', 'front_pose.py', 'fit_opposed.py', 'inspect_pose.py', 'fit_release_front.py', 'fit_akm_clearance.py', 'fit_akm_transition.py',
    'build_m4.py', 'build_akm.py', 'refresh_release.py', 'check_geometry.py', 'check_thumb_gun.py',
    'compare_thumb_gun.py', 'compare_source_self.py', 'validate_m4.py', 'verify_assets.py', 'import_assets.py',
    'assemble_editable.py', 'pose_quality.py', 'run.ps1', 'run_opposed.ps1',
    'make_opposed_delivery.py', 'validate_delivery.py',
    'opposed_acceptance.json', 'pose_quality.json', 'asset_validation.json', 'opposed_delivery_manifest.json',
    'reference_workflow_manifest.json', 'integration_baseline_manifest.json', 'runtime-integration.patch',
]
files += [p.relative_to(O).as_posix() for p in sorted((O / 'ReferenceWorkflow').glob('*.py'))]
files += [f'akm/{v}/thumb_transition.json' for v in ['vertical']]
files += [f'm4/{v}/release_front_validation.json' for v in ['vertical']]
files += [f'akm/{v}/thumb_gun_comparison.json' for v in ['vertical']]
paths = [p.relative_to(P).as_posix() for p in [O / n for n in files]]
paths += ['skills/ue5-fps-arms-animation/references/grip-arm-refinement.md', 'skills/ue5-fps-arms-animation/references/vertical-front-grasp.md']
assert len(paths) == len(set(paths))
assert all((P / p).is_file() for p in paths)
assert all((P / p).stat().st_size < 250000 for p in paths)
(O / 'public_files.txt').write_text('\n'.join(paths) + '\n', encoding='utf-8')
print('FRONT_DELIVERY_VALIDATION_PASS', len(paths), 'public files; 38 local source/export hashes; all README links', flush=True)
