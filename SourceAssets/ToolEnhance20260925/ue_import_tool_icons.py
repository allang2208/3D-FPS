# Re-import the rebaked factory-level (L1 stone) tool icons over the existing
# texture assets. Commandlet-safe: saves inside the run, writes a receipt.
import json
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
DEST = '/Game/ColdSteelData/ProductionTools'
TOOLS = u.AssetToolsHelpers.get_asset_tools()
report = {}
for name in ('axe', 'pickaxe_upright'):
    target = ROOT / 'Content/ColdSteelData/ProductionTools' / (name + '.png')
    task = u.AssetImportTask()
    task.filename = str(target)
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = False
    task.save = True
    TOOLS.import_asset_tasks([task])
    tex = u.load_asset(DEST + '/' + name)
    if tex is None:
        raise RuntimeError('Icon texture missing after import: ' + name)
    report[name] = {'asset': tex.get_path_name(),
                    'source_png': str(target.relative_to(ROOT)).replace('\\', '/')}
(ROOT / 'SourceAssets/ToolEnhance20260925/ue-icon-receipt.json').write_text(
    json.dumps(report, indent=2), encoding='utf-8')
