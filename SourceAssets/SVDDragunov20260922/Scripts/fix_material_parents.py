"""Repair the material-instance parents broken by the case-only renames.

The read-back showed MI_SVD_ChargingHandle and MI_SVD_SafetyLever with parent = null: the
rename to M_SVD_ChargingHandle / M_SVD_SafetyLever (via a temporary name) left those two
instances pointing at nothing. Every SVD instance parent is re-asserted here and verified.

Run:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / 'Config' / 'import_spec.json').read_text(encoding='utf-8-sig'))
BASE = SPEC['content_root']
E = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary

report = {'fixed': [], 'already_ok': [], 'failed': []}

for part in SPEC['parts']:
    mi_path = BASE + '/Materials/MI_SVD_' + part['part_name']
    m_path = BASE + '/Materials/M_SVD_' + part['part_name']
    mi = u.load_asset(mi_path)
    parent = u.load_asset(m_path)
    if not isinstance(mi, u.MaterialInstanceConstant) or not isinstance(parent, u.Material):
        report['failed'].append({'instance': mi_path, 'parent': m_path,
                                 'instance_found': mi is not None, 'parent_found': parent is not None})
        continue
    current = mi.get_editor_property('parent')
    if current == parent:
        report['already_ok'].append(part['part_name'])
        continue
    LIB.set_material_instance_parent(mi, parent)
    LIB.update_material_instance(mi)
    if not E.save_loaded_asset(mi, False):
        report['failed'].append({'instance': mi_path, 'reason': 'save failed'})
        continue
    report['fixed'].append({'part': part['part_name'],
                            'was': current.get_path_name().split('.')[0] if current else None})

# re-verify every instance parent
verify = {}
for part in SPEC['parts']:
    mi = u.load_asset(BASE + '/Materials/MI_SVD_' + part['part_name'])
    parent = mi.get_editor_property('parent') if isinstance(mi, u.MaterialInstanceConstant) else None
    verify[part['part_name']] = parent.get_path_name().split('.')[0] if parent else None
report['parents_after'] = verify
report['all_parents_ok'] = all(v == BASE + '/Materials/M_SVD_' + k for k, v in verify.items())

(ROOT / 'Receipts' / 'material_parent_fix.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print('PARENT_FIX ' + json.dumps(report, default=str))
