"""Install the saved, same-version UE packages at their original /Game paths."""
from pathlib import Path
from datetime import datetime, timezone
import json
import shutil

root = Path(__file__).resolve().parents[1]
project = root.parents[1]
source = root / 'UEImportHost/Content/Items/AlchemyMaterials20261015/V3'
destination = project / 'Content/Items/AlchemyMaterials20261015/V3'
imported = json.loads((root / 'Receipts/ue-import.json').read_text('utf-8'))
if imported['stage'] != 'staged_assets_saved':
    raise RuntimeError('Staging import must finish before installation')
files = sorted(p for p in source.rglob('*') if p.is_file())
if not files:
    raise RuntimeError('No saved packages to install')
for path in files:
    if path.suffix not in ('.uasset', '.uexp', '.ubulk'):
        raise RuntimeError('Unexpected staging file: ' + str(path))
    target = destination / path.relative_to(source)
    if target.exists():
        raise RuntimeError('Preserve existing target: ' + str(target))
report = dict(stage='installing', source=str(source), destination=str(destination),
              packages=[], runtime_tested=False, rendered=False)
receipt = root / 'Receipts/installation.json'
def save():
    receipt.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
save()
for path in files:
    target = destination / path.relative_to(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    with path.open('rb') as incoming, target.open('xb') as outgoing:
        shutil.copyfileobj(incoming, outgoing)
    report['packages'].append(dict(path=str(target), bytes=target.stat().st_size))
    save()
report.update(stage='assets_installed', installed_utc=datetime.now(timezone.utc).isoformat())
save()
print('POWER_TOOLS_PACKAGES_INSTALLED', len(report['packages']))
