"""Append the authored placements to current descriptors, preserving other fields."""
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
T = runpy.run_path(str(ROOT / 'treasure.py'))
paths = [
    'SourceAssets/DungeonAnatomyTheatre20261001/Pool20261001/Config/module.json',
    'SourceAssets/DungeonPowerTheme20261004RefineV2/Config/module-drafts.json',
    'SourceAssets/DungeonRoutes20260922/Config/catalog.json',
    'SourceAssets/DungeonThemedRoutes20261001/Config/catalog.json',
    'SourceAssets/DungeonSplitLevels20261001/Config/catalog.json',
    'SourceAssets/DungeonHospitalLine20261003/Config/production-catalog-snapshot.json',
]
updated = []
for relative in paths:
    path = PROJECT / relative
    if not path.exists():
        continue
    before = json.loads(path.read_text('utf8'))
    after = T['extend'](before) if 'modules' in before else T['extend_module'](before)
    if before == after:
        continue
    backup = ROOT / 'Backups/sources' / relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        backup.write_bytes(path.read_bytes())
    path.write_text(json.dumps(after, ensure_ascii=False, indent=2), encoding='utf8')
    updated.append(relative)
(ROOT / 'Receipts/source-updates.json').write_text(json.dumps(updated, indent=2), encoding='utf8')
print('TREASURE_SOURCE_DESCRIPTORS_WRITTEN', updated)
