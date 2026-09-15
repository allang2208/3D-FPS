"""Read package referencers for the user-authorized pistol archive."""
import json
from pathlib import Path
import unreal as u
root=Path(__file__).resolve().parents[2]
out=root/'Docs/Weapons/pistol-publication-20260915'
plan=json.loads((out/'archive-plan.json').read_text(encoding='utf-8'))
registry=u.AssetRegistryHelpers.get_asset_registry();registry.search_all_assets(True)
options=u.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True,
    include_searchable_names=True,include_soft_management_references=True,include_hard_management_references=True)
packages=set()
for row in plan['moves']:
    path=row['source']
    if not path.startswith('Content/'):continue
    package='/Game/'+path[len('Content/'):]
    if package.endswith('.uasset'):packages.add(package[:-7])
    else:packages.update(str(a.package_name) for a in registry.get_assets_by_path(package,True))
external=[]
for package in sorted(packages):
    for value in registry.get_referencers(package,options):
        if str(value) not in packages:external.append({'asset':package,'referencer':str(value)})
report={'packages':sorted(packages),'external_referencers':external,'scope':'Archive dependency check; no gameplay or visual testing'}
(out/'archive-references.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('PISTOL_ARCHIVE_REFERENCES packages='+str(len(packages))+' external='+str(len(external)))
