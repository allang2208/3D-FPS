"""Switch only SVCH's saved sight revision and its measured attachment frame."""
import json
from pathlib import Path

O = Path(__file__).parent
P = O.parents[2]
receipt = json.loads((O / 'install_receipt.json').read_text(encoding='utf-8'))
if not receipt.get('complete'):
    raise SystemExit('Finish saving the new UE mesh before activating it')
cal = json.loads((O / 'calibration.json').read_text(encoding='utf-8'))
header = P / 'Source/FPSGAME/Weapons/SVCHWeaponAssets.h'
text = header.read_text(encoding='utf-8')
text = text.replace('SourceAssets/SVCHReplacement20261018/calibration.json', 'SourceAssets/SVCHReplacement20261018/SightsR2/calibration.json')
text = text.replace('/Game/Weapons/SVCH/Replacement20261018/SK_SVCH_Replacement.SK_SVCH_Replacement', receipt['mesh'])
text = text.replace('Root = TEXT("/Game/Weapons/SVCH/Replacement20261018")', 'Root = TEXT("/Game/Weapons/SVCH/Replacement20261018/SightsR2")')
if 'SightHeightAboveRailCM' not in text:
    text = text.replace('inline constexpr float ADSRearEyeDistance = 10.f;', 'inline constexpr float ADSRearEyeDistance = 10.f;\n    inline constexpr float SightHeightAboveRailCM = 3.1f;')
for name in ('RearSight', 'FrontSight'):
    start = text.index('    inline const FVector ' + name + '(')
    end = text.index(';', start) + 1
    text = text[:start] + '    inline const FVector ' + name + '(' + ', '.join(f'{v:.12f}f' for v in cal[name]) + ');' + text[end:]
header.write_text(text, encoding='utf-8')
visual = P / 'Source/FPSGAME/Weapons/M4GunsmithVisual.cpp'
text = visual.read_text(encoding='utf-8')
text = text.replace('RailDrop=bSVCH?3.8f:', 'RailDrop=bSVCH?SVCHWeaponAssets::SightHeightAboveRailCM:')
visual.write_text(text, encoding='utf-8')
registry = P / 'Source/FPSGAME/Characters/FPSPreloadAssetRegistry.gen.h'
text = registry.read_text(encoding='utf-8')
# Only replace the two existing SVCH literals; preserve concurrent registry edits.
text = text.replace('TEXT("/Game/Weapons/SVCH/Replacement20261018"),', 'TEXT("/Game/Weapons/SVCH/Replacement20261018/SightsR2"),')
text = text.replace('TEXT("/Game/Weapons/SVCH/Replacement20261018/SK_SVCH_Replacement"),', 'TEXT("/Game/Weapons/SVCH/Replacement20261018/SightsR2/SK_SVCH_SightsR2"),')
registry.write_text(text, encoding='utf-8')
(O / 'activation_receipt.json').write_text(json.dumps({'mesh': receipt['mesh'], 'profile_preserved': True, 'rear': cal['RearSight'], 'front': cal['FrontSight'], 'build_complete': False}, indent=2))
print('SVCH sight references updated; native build remains required')
