import json,re
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2]
r=json.loads((O/'install_receipt.json').read_text());cal=json.loads((O/'calibration.json').read_text());assert r['complete']
old='/Game/Weapons/SVCH/Replacement20261018/SightsR2/ElbowFit/SK_SVCH_SightsR2_ElbowFit'
new=r['mesh'].split('.')[0]
p=P/'Source/FPSGAME/Weapons/SVCHWeaponAssets.h';s=p.read_text(encoding='utf-8')
s=s.replace(old+'.SK_SVCH_SightsR2_ElbowFit',r['mesh'])
s=s.replace('SightsR2/elbow_calibration.json','RealSights20261019/calibration.json')
s=re.sub(r'(inline constexpr const TCHAR\* Root = TEXT\(")[^"]+("\);)',lambda m:m[1]+new.rsplit('/',1)[0]+m[2],s)
for name in ['RearSight','FrontSight']:
 s=re.sub(r'inline const FVector '+name+r'\([^;]+;', 'inline const FVector '+name+'('+', '.join(f'{v:.12f}f' for v in cal[name])+');',s)
# Preserve the existing scope's absolute rail mount as rear iron moves forward.
s=re.sub(r'inline constexpr float OpticAlongCM = [^;]+;[^\n]*','inline constexpr float OpticAlongCM = 9.918044f; // Same absolute optic mount; measured rear iron moved onto the rail.',s)
p.write_text(s,encoding='utf-8')
p=P/'Source/FPSGAME/Characters/FPSPreloadAssetRegistry.gen.h';s=p.read_text(encoding='utf-8');s=s.replace('TEXT("'+old+'")','TEXT("'+new+'")')
# Keep the existing grip-profile dependency; only mesh and mesh root change.
s=s.replace('TEXT("/Game/Weapons/SVCH/Replacement20261018/SightsR2/ElbowFit"),','TEXT("'+new.rsplit('/',1)[0]+'"),');p.write_text(s,encoding='utf-8')
(O/'activation_receipt.json').write_text(json.dumps({'mesh':r['mesh'],'unchanged_profile':r['profile'],'rear':cal['RearSight'],'front':cal['FrontSight'],'optic_mount_preserved':True,'runtime_tested':False},indent=2))
print('REAL_SVCH_SIGHTS_ACTIVATED')
