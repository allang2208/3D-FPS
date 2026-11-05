"""Capture the active M24 layers and raw poses used by the bolt paths."""
from pathlib import Path
import ast, gzip, hashlib, json
import unreal as u

O = Path(__file__).resolve().parent
source = O.parent / 'M24QuickMeleeRightHandR3_20261104' / 'read_inputs.py'
code = source.read_text().split('assembly={')[0]
roles = ('A_M24_idle','A_M24_aim','A_M24_fire','A_M24_cycle','A_M24_equip','A_M24_reload_empty')
code = code.replace("('A_M24_idle','A_M24_quick_melee')", repr(roles))
exec(compile(code, 'read active profiles and bolt sources', 'exec'))
(O/'input_assets.json').write_text(json.dumps(assets,indent=2))
(O/'input_dependency_hashes.json').write_text(json.dumps(hashes,indent=2))
print('BOLT_INPUTS', {key:[c['base'].split('.')[-1] for c in value['clips']] for key,value in profiles.items()}, flush=True)
