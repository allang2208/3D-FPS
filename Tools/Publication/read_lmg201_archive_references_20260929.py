"""Resolve external package referencers before retiring old 201 packages."""
import json
from pathlib import Path
import unreal as u

root=Path(__file__).resolve().parents[2]
out=root/'Docs/Weapons/lmg201-publication-20260929'
plan=json.loads((out/'archive-plan.json').read_text(encoding='utf-8'))
registry=u.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
opts=u.AssetRegistryDependencyOptions(include_soft_package_references=True,
    include_hard_package_references=True,include_searchable_names=True,
    include_soft_management_references=True,include_hard_management_references=True)
files={'/Game/'+p[8:-7]:p for p in plan['content_candidates']}
refs={p:{str(x) for x in registry.get_referencers(p,opts)} for p in files}
archive=set(files)
while True:
    retained={p for p in archive if refs[p]-archive}
    if not retained:break
    archive-=retained
report=dict(packages=sorted(archive),retained=[dict(package=p,referencers=sorted(refs[p]-archive)) for p in sorted(set(files)-archive)],
    external_referencers=[], scope='User-requested archive dependency check only')
for p in sorted(archive):
    plan['moves'].append(dict(source=files[p],reason='Retired 201 package with no external package referencers',replacement='Current Cover10/Repair36, ClothFeed33, Magazine24 and base animations'))
(out/'archive-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(out/'archive-references.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
u.log('LMG201_ARCHIVE packages='+str(len(archive))+' retained='+str(len(report['retained'])))
