"""Read package references for the explicitly retired M27 revisions; no writes to assets."""
import json
from pathlib import Path
import unreal as u

root = Path('D:/FPS3D/FPSGAME')
revisions = ['ClawV7', 'ClawV12', 'ClawV13', 'PounceV9', 'PounceV10']
registry = u.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
packages = {str(a.package_name) for revision in revisions for a in
            registry.get_assets_by_path('/Game/Monsters/MantisM27/' + revision, recursive=True)}
options = u.AssetRegistryDependencyOptions(True, True, True, True, True)
refs = {p: sorted(str(r) for r in registry.get_referencers(p, options)) for p in sorted(packages)}
# A candidate referenced by a retained package must remain; propagate that rule
# through the candidate set before reporting movable packages.
movable = set(packages)
while True:
    retained = {p for p in movable if any(r not in movable for r in refs[p])}
    if not retained:
        break
    movable -= retained
out = root / 'Saved/MantisM27Publication20261007'
out.mkdir(parents=True, exist_ok=True)
report = dict(revisions=revisions, referencers=refs, movable_packages=sorted(movable),
              retained_packages=sorted(packages-movable), gameplay_tested=False)
(out / 'asset-references.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('M27_RETIREMENT_REFERENCES ' + json.dumps(dict(packages=len(packages), movable=len(movable), retained=report['retained_packages'])), flush=True)
