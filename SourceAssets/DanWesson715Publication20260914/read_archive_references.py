"""Read referencers before archiving only the two user-rejected 715 revisions."""
import json
from pathlib import Path
import unreal as u

roots = ['/Game/Weapons/DanWesson715/Precision20260914', '/Game/Weapons/DanWesson715/Polish20260914']
registry = u.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
options = u.AssetRegistryDependencyOptions(include_soft_package_references=True,
    include_hard_package_references=True, include_searchable_names=True,
    include_soft_management_references=True, include_hard_management_references=True)
packages = sorted({str(a.package_name) for root in roots for a in registry.get_assets_by_path(root, True)})
external = []
for package in packages:
    for value in registry.get_referencers(package, options):
        name = str(value)
        if not any(name.startswith(root + '/') for root in roots):
            external.append({'asset': package, 'referencer': name})
report = {'retired_roots': roots, 'packages': packages, 'external_referencers': external,
          'scope': 'Archive dependency check only; no game or visual testing'}
(Path(__file__).parent/'archive-references.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
u.log('DW715_ARCHIVE_REFERENCES packages=' + str(len(packages)) + ' external=' + str(len(external)))
