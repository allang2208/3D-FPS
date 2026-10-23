"""Collect the production receipts; does not run a game or any acceptance tests."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
def read(name):return json.loads((P/name).read_text(encoding='utf-8-sig'))
delivery={'weapon':'ue_runebound_warhammer','revision':'ModulesV1_HostSectionFit',
    'tested':False,'editor_ui_started':False,'game_started':False,
    'factory_parts':read('exports.json')['parts'],'shared_fitted_parts':read('adapted_exports.json')['parts'],
    'shared_libraries':{'hammer_heads':'common-hammer-heads.json','head_mount':'common-hammer-seats.json',
        'grip':'common-hammer-grips.json','pommel':'common-hammer-pommels.json','rune':'melee-gunsmith.json:blade_2 (five common runes)'},
    'factory_surface_policy':'Clip the original triangles, interpolate corner UV and normal, cap only new cuts',
    'fit_policy':'Source and host installation section rings; smooth local deformation; host native material and projected connector UV',
    'rune_policy':'Shared masks, palettes and effects; host-local bare-shaft cylinder 42.5 to 76 cm',
    'animation_policy':'Existing first/third-person motion, grip profile and action clocks unchanged; no animation assets rewritten',
    'exclusive_parts':'meteor_core remains exclusive to ue_steel_warhammer',
}
for name,key in [('build_receipt.json','builds'),('import_receipt.json','import')]:
    if (P/name).exists():delivery[key]=read(name)
(P/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf-8')
print('Modular hammer production delivery recorded')
