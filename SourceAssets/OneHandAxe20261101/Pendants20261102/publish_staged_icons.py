"""Publish new packages only; never overwrite a loaded/shared asset."""
import json
from pathlib import Path

P = Path(__file__).resolve().parent
receipt_path = P / 'icon_import_receipt.json'
receipt = json.loads(receipt_path.read_text('utf-8'))
if not receipt['complete']:
    raise RuntimeError('Staged icon saving did not complete')
source = P / 'ImportProject/Content/ColdSteelData/AttachmentIcons20260913'
target = P.parents[2] / 'Content/ColdSteelData/AttachmentIcons20260913'
for key in ['category_lanyard', 'lanyard_false']:
    for asset in source.glob(key + '.*'):
        if asset.suffix not in {'.uasset', '.uexp', '.ubulk'}:
            continue
        with (target / asset.name).open('xb') as dest:
            dest.write(asset.read_bytes())
receipt['staging_project_dir'] = receipt['project_dir']
receipt['project_dir'] = str(P.parents[2])
receipt['saved_to_target_project'] = True
receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print('SHARED_PENDANT_ICON_PACKAGES_PUBLISHED')
