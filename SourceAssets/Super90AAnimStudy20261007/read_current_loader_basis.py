"""Read current loader author inputs only; do not author/export/save animation."""
import json
from pathlib import Path

output = Path(__file__).parent
source = output.parent / 'Super90Speedloader20261007/author_speedloader.py'
code = source.read_text(encoding='utf-8-sig').split('# Transfer the already accepted vertical cylindrical grasp')[0]
scope = {'__file__': str(source)}
exec(compile(code, str(source), 'exec'), scope)

rows = {}
for family, pose in scope['idles'].items():
    shoulder = pose['upperarm_l'].translation
    elbow = pose['lowerarm_l'].translation
    wrist = pose['hand_l'].translation
    rows[family] = {'left_arm_author_units': (elbow-shoulder).length + (wrist-elbow).length,
                    'hand_matrix_scale': list(pose['hand_l'].to_scale()),
                    'root_matrix_scale': list(pose['VM_Root'].to_scale())}
base_length = rows['base']['left_arm_author_units']
for row in rows.values():
    row['arm_length_ratio_to_base'] = row['left_arm_author_units'] / base_length
report = {'source': str(source), 'families': rows,
          'scope': 'Read current loader inputs; no export, asset import, render or game run.'}
(output / 'current_loader_basis.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('CURRENT_LOADER_BASIS', json.dumps(rows), flush=True)
