import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;root='/Game/Weapons/M16A2/UniversalAttachments20260920/AuthoringRecovery'
ar=u.AssetRegistryHelpers.get_asset_registry();assets=ar.get_assets_by_path(root,recursive=True);rows=[]
opts=u.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True,include_searchable_names=False,include_soft_management_references=True,include_hard_management_references=True)
for a in assets:
 p=str(a.package_name);refs=[str(x) for x in ar.get_referencers(p,opts)]
 rows.append({'package':p,'loaded':a.is_asset_loaded(),'external_referencers':[x for x in refs if not x.startswith(root+'/')]})
(O/'retired_asset_references.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('M16_RETIRED_ASSETS',len(rows),'loaded',sum(x['loaded'] for x in rows),'external_referencers',sum(len(x['external_referencers']) for x in rows))
