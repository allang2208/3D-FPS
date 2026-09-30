"""Read referencers of superseded charcoal packages before local archival."""
import json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/OutfitCloseout20260930'
base=P/'Content/Characters/ModularOutfit20260924/CharcoalGarmentRepair20260930'
folders=['Body','BodyV2','BodyV3','Traversal','Pickups','PickupsV2']
paths=[p for name in folders for p in (base/name).rglob('*.uasset')]
packages={'/Game/'+p.relative_to(P/'Content').with_suffix('').as_posix() for p in paths}
ar=u.AssetRegistryHelpers.get_asset_registry();ar.search_all_assets(True);ar.wait_for_completion()
opts=u.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True,include_searchable_names=True,include_soft_management_references=True,include_hard_management_references=True)
rows=[]
for path in sorted(packages):
 refs=[str(n) for n in ar.get_referencers(path,opts)]
 rows.append(dict(package=path,referencers=refs,outside_candidates=[n for n in refs if n not in packages]))
(R/'asset-referencers.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('OUTFIT_ARCHIVE_REFERENCE_READ',len(rows),'externally_referenced',sum(bool(r['outside_candidates']) for r in rows))
