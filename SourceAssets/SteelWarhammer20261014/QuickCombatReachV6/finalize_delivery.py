"""Record the saved V6 asset and formal builds; update compatibility entries."""
import json
from datetime import datetime
from pathlib import Path

p = Path(__file__).resolve().parent
imported = json.loads((p / 'import_receipt.json').read_text(encoding='utf-8-sig'))
built = json.loads((p / 'build_receipt.json').read_text(encoding='utf-8-sig'))
authored = json.loads((p / 'authored.json').read_text(encoding='utf-8-sig'))
if not imported['complete'] or imported['revision'] != 'HeadThrustReachV6_20261015':
    raise RuntimeError('V6 animation is not saved')
if not built['complete'] or any(target['exit_code'] for target in built['targets']):
    raise RuntimeError('Formal builds are incomplete')
for old in ('QuickCombatV1', 'QuickCombatImpactV2'):
    backup = p / 'Before' / old
    backup.mkdir(exist_ok=True)
    for entry, target in (('author_quick_combat.py', 'author_head_thrust.py'),
                          ('import_assets.py', 'import_assets.py')):
        old_path = p.parent / old / entry
        if not (backup / entry).exists():
            (backup / entry).write_bytes(old_path.read_bytes())
        old_path.write_text(
            '"""Current warhammer quick melee: longer forward thrust V6."""\n'
            'from pathlib import Path\nimport runpy\n'
            'runpy.run_path(str(Path(__file__).resolve().parent.parent/'
            f'"QuickCombatReachV6/{target}"),run_name="__main__")\n', encoding='utf-8')
receipt = {
    'revision': imported['revision'], 'saved_assets': imported['saved'],
    'builds': built['targets'], 'runtime_seconds': .72, 'prepare_seconds': .22,
    'contact_seconds': .28, 'follow_seconds': .34, 'withdraw_end_seconds': .54,
    'source_seconds': authored['seconds'], 'forward_stroke_m': .34,
    'contact_forward_stroke_m': .29, 'native_grip_and_bone_lengths_preserved': True,
    'previous_asset_preserved': '/Game/Weapons/SteelWarhammer20261014/QuickCombatV1/A_Warhammer_QuickCombat',
    'gameplay_damage_range_cost_changed': False,
    'runtime_tested': False, 'multiplayer_tested': False, 'preview_rendered': False,
    'finished': datetime.now().isoformat(timespec='seconds'),
}
(p / 'delivery.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print(json.dumps(receipt))
