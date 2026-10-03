"""Explicit offline rollback; never invoked automatically by production.

Run only with UE closed, using the V35 Before/Content original packages. This
restores their original internal package names and deactivates V35 overrides.
"""
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
processes = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, text=True, check=True).stdout.lower()
if 'unrealeditor.exe' in processes or 'unrealeditor-cmd.exe' in processes:
    raise RuntimeError('Close Unreal normally before offline rollback; no process was stopped.')
inputs = json.loads((ROOT / 'inputs-receipt.json').read_text(encoding='utf-8'))
for entry in inputs['backups']:
    relative = Path(entry['target'].removeprefix('/Game/') + '.uasset')
    source = ROOT / 'Before/Content' / relative
    target = PROJECT / 'Content' / relative
    if not source.is_file() or not target.resolve().is_relative_to((PROJECT / 'Content').resolve()):
        raise RuntimeError('Missing or out-of-project original package ' + str(source))
for entry in inputs['backups']:
    relative = Path(entry['target'].removeprefix('/Game/') + '.uasset')
    shutil.copy2(ROOT / 'Before/Content' / relative, PROJECT / 'Content' / relative)
receipt_path = ROOT / 'install-receipt.json'
if receipt_path.exists():
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    receipt['complete'] = False
    receipt['restored_original_packages'] = True
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('STAFF_QUARTZ_V35_ORIGINAL_PACKAGES_RESTORED')
