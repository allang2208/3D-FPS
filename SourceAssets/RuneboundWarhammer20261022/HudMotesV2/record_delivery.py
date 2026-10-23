"""Record completed production saves and native builds, without running acceptance tests."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
imported = json.loads((P/'import_receipt.json').read_text(encoding='utf-8-sig'))
built = json.loads((P/'build_receipt.json').read_text(encoding='utf-8-sig'))
ready = {r['target'] for r in built['targets'] if r['exit_code'] == 0}
if not imported.get('installed_to_main_project') or ready != {'FPSGAME', 'FPSGAMEEditor'}:
    raise RuntimeError('Finish saved-asset installation and both native targets first')
sources = [P.parent/'PassiveV1/RuneboundEnergyHud.hlsl', ROOT/'Source/FPSGAME/Production/RuneboundHammerTuning.h',
           P/'author_isolated.py', P/'install_assets.py']
receipt = {
    'complete': True, 'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
    'weapon': 'ue_runebound_warhammer', 'scope': 'left energy HUD only',
    'material': imported['asset'], 'installed_files': imported['installed_files'],
    'builds': built['targets'],
    'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
    'removed': ['seven floating diamond crystal ornaments', 'central faceted diamond and rigid strokes'],
    'replacement': {'gathering_motes': 10, 'rising_motes': 22, 'soft_nebula': True, 'short_light_tails': True},
    'slate_material_quads': 1, 'gameplay_balance_modified': False, 'shared_azure_dragon_assets_modified': False,
    'tests_run': False, 'game_started': False, 'editor_ui_started': False, 'rendered_acceptance': False,
}
(P/'delivery_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('RUNEBOUND_HUD_MOTES_V2_DELIVERED')
