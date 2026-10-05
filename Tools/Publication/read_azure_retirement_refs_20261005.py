"""Read only: dependency boundary for the explicitly requested Azure Dragon archive."""
import json
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/AzureDragonPublication20261005'
OUT.mkdir(parents=True,exist_ok=True)
registry=u.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
prefix='/Game/Weapons/AzureDragon20261004'
candidates=[]
for folder in ('RigV2','EnergyV3','EnergyV6','Meshes'):
    candidates += list(u.EditorAssetLibrary.list_assets(prefix+'/'+folder,True,False))
packages={str(p).split('.')[0] for p in candidates}
options=u.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True,
    include_searchable_names=True,include_soft_management_references=True,include_hard_management_references=True)
entries=[]
for package in sorted(packages):
    refs=sorted(str(p) for p in registry.get_referencers(package,options))
    external=[p for p in refs if p not in packages]
    entries.append(dict(package=package,referencers=refs,external_referencers=external))
result=dict(scope=prefix,candidates=entries,external_count=sum(bool(e['external_referencers']) for e in entries),
            read_only=True,runtime_tested=False)
(OUT/'asset-retirement-references.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('AZURE_RETIREMENT_REFERENCES packages='+str(len(entries))+' external='+str(result['external_count']))
