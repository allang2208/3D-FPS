"""Publication-only dependency inventory; no live components or asset writes."""
import json
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME')
R = P / 'SourceAssets/LowerEquipmentPublication20261006'
roots = [
    '/Game/Characters/ModularOutfit20260924/FirstPersonLegs20261004',
    '/Game/Characters/ModularOutfit20260924/OwnerBodyShared20261005',
]
registry = u.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
packages = {str(a.package_name) for root in roots
            for a in registry.get_assets_by_path(root, recursive=True)}
options = u.AssetRegistryDependencyOptions(
    include_soft_package_references=True, include_hard_package_references=True,
    include_searchable_names=True, include_soft_management_references=True,
    include_hard_management_references=True)
report = {package: [str(ref) for ref in registry.get_referencers(package, options)
                    if str(ref) not in packages] for package in sorted(packages)}
R.mkdir(parents=True, exist_ok=True)
(R / 'retired-asset-references.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('RETIRED_ASSET_REFERENCES ' + json.dumps({'packages': len(packages),
      'external_referencers': {p: r for p, r in report.items() if r}}), flush=True)
