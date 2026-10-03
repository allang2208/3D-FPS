import json
from pathlib import Path
import unreal as u
base='/Game/Realistic_Starter_VFX_Pack_Vol2/'
paths=[base+'Particles/Fire/'+n for n in ['P_Fire_Small','P_Fire_Big','P_flamethrower','P_Fire_Wall']]
paths += [base+'Particles/Explosion/'+n for n in ['P_Molotov','P_Explosion_Big_A','P_Explosion_Big_B','P_Explosion_Big_C']]
paths += ['/Game/MilitaryTrench/Particles/P_Fire','/Game/EasyBuildingSystem/Effects/PS_CampFire','/Game/EasyBuildingSystem/Effects/PS_TorchFire','/Game/NiagaraExamples/FX_Misc/NS_Fire','/Game/RPGEnvironmentVFX/VFX/Niagara/NS_CauldronBlacksmith']
rows=[]
registry=u.AssetRegistryHelpers.get_asset_registry()
options=u.AssetRegistryDependencyOptions(include_soft_package_references=False,include_hard_package_references=True)
for path in paths:
    obj=u.load_asset(path)
    row={'path':path,'class':obj.get_class().get_name() if obj else None,'materials':[]}
    if obj:
        row['materials']=[str(dep) for dep in registry.get_dependencies(path,options) if '/M_' in str(dep) or '/MI_' in str(dep) or '/MM_' in str(dep)]
    rows.append(row)
out=Path(u.Paths.project_dir()).resolve()/'SourceAssets/FireAlternatives20260921'
out.mkdir(parents=True,exist_ok=True)
(out/'inventory.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print(json.dumps(rows,indent=2))
