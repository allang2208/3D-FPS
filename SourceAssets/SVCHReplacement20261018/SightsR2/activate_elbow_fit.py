import json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];receipt=json.loads((O/'elbow_install_receipt.json').read_text());cal=json.loads((O/'elbow_calibration.json').read_text())
assert receipt['complete']
header=P/'Source/FPSGAME/Weapons/SVCHWeaponAssets.h';s=header.read_text(encoding='utf-8')
s=s.replace('/SightsR2/BoltFit','/SightsR2/ElbowFit').replace('SK_SVCH_SightsR2_BoltFit','SK_SVCH_SightsR2_ElbowFit').replace('DA_SVCH_BoltFitGrip','DA_SVCH_ElbowFitGrip').replace('SightsR2/calibration.json','SightsR2/elbow_calibration.json')
if 'OpticAlongCM' not in s:s=s.replace('inline constexpr float SightHeightAboveRailCM = 3.1f;', 'inline constexpr float SightHeightAboveRailCM = 3.1f;\n    inline constexpr float OpticAlongCM = 14.5f; // Preserve the optic mount when moving the rear iron back 6.5 cm.')
for name in ('RearSight','FrontSight'):
 start=s.index('    inline const FVector '+name+'(');end=s.index(';',start)+1;s=s[:start]+'    inline const FVector '+name+'('+', '.join(f'{v:.12f}f' for v in cal[name])+');'+s[end:]
header.write_text(s,encoding='utf-8')
registry=P/'Source/FPSGAME/Characters/FPSPreloadAssetRegistry.gen.h';s=registry.read_text(encoding='utf-8').replace('/SightsR2/BoltFit','/SightsR2/ElbowFit').replace('SK_SVCH_SightsR2_BoltFit','SK_SVCH_SightsR2_ElbowFit').replace('DA_SVCH_BoltFitGrip','DA_SVCH_ElbowFitGrip');registry.write_text(s,encoding='utf-8')
visual=P/'Source/FPSGAME/Weapons/M4GunsmithVisual.cpp';s=visual.read_text(encoding='utf-8').replace('const float Along=bUseASH12?', 'const float Along=bSVCH?SVCHWeaponAssets::OpticAlongCM:bUseASH12?');visual.write_text(s,encoding='utf-8')
(O/'elbow_activation_receipt.json').write_text(json.dumps({'mesh':receipt['mesh'],'profile':receipt['profile'],'rear':cal['RearSight'],'front':cal['FrontSight'],'optic_position_preserved':True},indent=2));print('SVCH rear sight clearance and palm-preserving profile references saved')
