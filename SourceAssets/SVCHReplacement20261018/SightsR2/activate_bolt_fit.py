import json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];r=json.loads((O/'bolt_install_receipt.json').read_text())
assert r['complete']
oldmesh='/Game/Weapons/SVCH/Replacement20261018/SightsR2/SK_SVCH_SightsR2.SK_SVCH_SightsR2'
oldprofile='/Game/Weapons/SVCH/Replacement20261018/DA_SVCH_ReplacementGrip.DA_SVCH_ReplacementGrip'
header=P/'Source/FPSGAME/Weapons/SVCHWeaponAssets.h';s=header.read_text(encoding='utf-8')
s=s.replace(oldmesh,r['mesh']).replace(oldprofile,r['profile']).replace('Root = TEXT("/Game/Weapons/SVCH/Replacement20261018/SightsR2")','Root = TEXT("/Game/Weapons/SVCH/Replacement20261018/SightsR2/BoltFit")');header.write_text(s,encoding='utf-8')
registry=P/'Source/FPSGAME/Characters/FPSPreloadAssetRegistry.gen.h';s=registry.read_text(encoding='utf-8')
s=s.replace('TEXT("'+oldmesh.split('.')[0]+'")','TEXT("'+r['mesh'].split('.')[0]+'")').replace('TEXT("'+oldprofile.split('.')[0]+'")','TEXT("'+r['profile'].split('.')[0]+'")').replace('TEXT("/Game/Weapons/SVCH/Replacement20261018/SightsR2")','TEXT("/Game/Weapons/SVCH/Replacement20261018/SightsR2/BoltFit")');registry.write_text(s,encoding='utf-8')
print('SVCH bolt bind and matched contact profile references saved')
