"""Validate the scoped source package without rebuilding animation assets."""
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

O = Path(__file__).resolve().parent
P = O.parents[1]
scripts = [
    'audit_m4.py', 'prepare_canted_final.py', 'build_canted.py', 'prepare_akm.py',
    'build_akm.py', 'check_geometry.py', 'validate_m4.py', 'compare_source_self.py',
    'import_assets.py', 'verify_assets.py', 'export_pose_reference.py', 'verify_pose_reference.py',
    'assemble_editable.py', 'make_delivery.py', 'package_integration.py', 'validate_delivery.py',
    'ReferenceWorkflow/m4_build_family.py', 'ReferenceWorkflow/inspect_reference.py',
    'ReferenceWorkflow/validate_source.py', 'ReferenceWorkflow/akm_preview_visibility.py']
for name in scripts:
    ast.parse((O / name).read_text(encoding='utf-8-sig'), filename=name)
for path in [O / 'README.md', P / 'Docs/CantedGripMigration.md', P / 'skills/ue5-fps-arms-animation/references/canted-akm-migration.md']:
    for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
        if '://' not in target:
            assert (path.parent / target).exists(), (path, target)
for name, entry in json.loads((O / 'ReferenceWorkflow/hashes.json').read_text()).items():
    assert hashlib.sha256((O / 'ReferenceWorkflow' / name).read_bytes()).hexdigest() == entry['sha256']
for entry in json.loads((O / 'delivery_manifest.json').read_text()):
    assert (O / entry['path']).stat().st_size == entry['bytes']
project_skill = P / 'skills/ue5-fps-arms-animation/references/canted-akm-migration.md'
personal_skill = Path('C:/Users/allan/.codex/skills/ue5-fps-arms-animation/references/canted-akm-migration.md')
assert project_skill.read_bytes() == personal_skill.read_bytes()
subprocess.run(['git', 'apply', '--check', '--unidiff-zero', '--ignore-space-change', '--directory=SourceAssets/CantedGripMigration20260911/Baseline', str(O / 'Integration/runtime.patch')], cwd=P, check=True)
public = ['SourceAssets/CantedGripMigration20260911/' + name for name in scripts + [
    'README.md', 'run.ps1', 'run_final.ps1', 'acceptance.json', 'asset_validation.json',
    'catalog_parity.json', 'delivery_manifest.json', 'ReferenceWorkflow/hashes.json',
    'Integration/runtime.patch', 'Integration/manifest.json']]
public += ['Docs/CantedGripMigration.md', 'skills/ue5-fps-arms-animation/references/canted-akm-migration.md', 'skills/ue5-fps-arms-animation/references/grip-arm-refinement.md']
(O / 'publication_paths.txt').write_text('\n'.join(public) + '\n', encoding='utf-8')
print('DELIVERY_PACKAGE_PASS', len(scripts), 'python files;', len(public), 'scoped public files')
