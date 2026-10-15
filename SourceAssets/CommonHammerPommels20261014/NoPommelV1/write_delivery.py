"""Record completed authoring, asset saves and native build receipts; no tests run."""
import json
import runpy
from pathlib import Path

P = Path(__file__).resolve().parent

def read(name):
    return json.loads((P / name).read_text(encoding='utf-8-sig'))

delivery = {
    'option': runpy.run_path(str(P / 'catalog.py'))['OPTION'],
    'shared_slot': 'pommel',
    'host': 'ue_steel_warhammer',
    'weighted_body_removed': True,
    'retained_end_depth_mm': 3.2,
    'icon_reused_from': 'Content/ColdSteelData/AttachmentIcons20260913/rune_false.png',
    'assets': read('import_receipt.json'),
    'commandlet': read('commandlet_receipt.json'),
    'editor_build': read('editor-build-receipt.json'),
    'game_build': read('game-build-receipt.json'),
    'cost_rule': 'Normal cost * 0.95; charged heavy release cost additionally * 1.10. Sprint attacks and weapon skills do not receive the heavy-release surcharge.',
    'single_option_normal_stamina_ratio': 0.95,
    'single_option_charged_heavy_stamina_ratio': 1.045,
    'heavy_release_authority_paths': ['standalone', 'server'],
    'ui': ['selected attachment', 'gunsmith overview', 'item tooltip', 'item comparison summary'],
    'previous_pointed_hammer_penetration_readout_completed': True,
    'game_tested': False,
    'tests_run': False,
    'editor_gui_launched': False,
    'runtime_acceptance': 'User testing pending'
}
if (P / 'GameAttempt1/game-build-receipt.json').exists():
    delivery['game_build_first_attempt'] = read('GameAttempt1/game-build-receipt.json')
    delivery['game_build_retry_reason'] = 'TransitLoadingSubsystem.h changed during the first build; UHT-generated macro line numbers became stale. No loading subsystem source was changed by this task.'
(P / 'delivery.json').write_text(json.dumps(delivery, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('NO_POMMEL_DELIVERY_WRITTEN')
