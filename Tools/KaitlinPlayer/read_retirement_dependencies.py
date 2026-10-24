"""Read package referencers before the explicitly requested retirement operation."""
import json
from pathlib import Path
import unreal as u
def main():
    p=Path('D:/FPS3D/FPSGAME');w=p/'SourceAssets/KaitlinPublication20261024'
    plan=json.loads((w/'retirement_plan.json').read_text('utf-8'))
    registry=u.AssetRegistryHelpers.get_asset_registry();registry.search_all_assets(True)
    candidates=set(plan['packages']);result={}
    for package in candidates:
        references=[str(x) for x in registry.get_referencers(package,u.AssetRegistryDependencyOptions())]
        result[package]={'referencers':references,'external_referencers':[x for x in references if x not in candidates]}
    (w/'package_referencers.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (p/'SourceAssets/KaitlinPlayer20261023/read_retirement_dependencies_status.json').write_text(json.dumps({'remaining':0,'complete':True}))
    print('RETIREMENT_REFERENCERS',len(result),'external',sum(bool(x['external_referencers']) for x in result.values()))
main()
