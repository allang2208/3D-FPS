"""Apply the requested 180 degree turn in TangDao's weapon-local grip space."""
import copy
import json
import math
from pathlib import Path

P = Path(__file__).resolve().parent
catalog_path = P.parents[1] / 'Content/ColdSteelData/tang-dao-modules.json'
orientation_path = P / 'holding_orientation.json'
catalog = json.loads(catalog_path.read_text(encoding='utf-8-sig'))

if orientation_path.exists():
    orientation = json.loads(orientation_path.read_text(encoding='utf-8'))
else:
    backup = P / 'Before/HoldingDirection20261002'
    backup.mkdir(parents=True, exist_ok=True)
    (backup / catalog_path.name).write_bytes(catalog_path.read_bytes())
    base = copy.deepcopy(catalog['bone_mount'])
    mount = copy.deepcopy(base)
    x, y, z, w = base['rotation_xyzw']
    # Original mount quaternion * local +Z half-turn quaternion (0, 0, 1, 0).
    turned = [y, -x, w, -z]
    length = math.sqrt(sum(value * value for value in turned))
    mount['rotation_xyzw'] = [value / length for value in turned]
    orientation = {
        'weapon': 'ue_tang_dao',
        'revision': 'holding_direction_flip_20261002',
        'local_axis': [0, 0, 1],
        'local_rotation_degrees': 180,
        'baseline_bone_mount': base,
        'bone_mount': mount,
        'reason': 'User requested swapping the blade edge and spine facing directions.',
        'tested': False,
    }
    orientation_path.write_text(json.dumps(orientation, indent=2) + '\n', encoding='utf-8')

# Set the recorded result directly so rerunning this script does not toggle it.
catalog['bone_mount'] = copy.deepcopy(orientation['bone_mount'])
temporary = catalog_path.with_suffix('.json.holding.tmp')
temporary.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
temporary.replace(catalog_path)
print('TANGDAO_HOLDING_DIRECTION_SAVED local_Z=180_degrees; tested=False')
