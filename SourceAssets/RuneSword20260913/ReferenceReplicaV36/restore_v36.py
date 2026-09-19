"""Restore the exact V36 Inspect saved before the V37 import.

Only replaces the existing Inspect asset. A running editor may keep the target
file open; in that case replacement fails without overwriting its contents.
"""
import json
import os
import shutil
from pathlib import Path

P = Path(__file__).parent
ROOT = P.parents[2]
source = P.parent / 'ShoulderOutsideInspectV37/Before/A_RuneSword_Inspect.uasset'
target = ROOT / 'Content/Weapons/AzureRunesword20260913/A_RuneSword_Inspect.uasset'
record = P / 'Before/RestoreFromV38'
record.mkdir(parents=True, exist_ok=True)
backup = record / 'A_RuneSword_Inspect.uasset'
if not backup.exists():
    shutil.copy2(target, backup)
staged = record / 'V36_pending.uasset'
shutil.copy2(source, staged)
os.replace(staged, target)
(record / 'restore_receipt.json').write_text(json.dumps({
    'restored_revision': 'ReferenceReplicaV36',
    'source': str(source), 'target': str(target),
    'previous_asset_backup': str(backup),
    'method': 'Exact pre-V37 V36 asset restored; no animation rebuild',
    'testing': 'No playback or game testing performed'
}, indent=2), encoding='utf-8')
print('V36_RESTORED', str(target))
