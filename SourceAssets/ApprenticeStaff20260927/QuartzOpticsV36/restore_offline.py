"""Explicitly restore only the two pre-V36 material packages with UE closed."""
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
processes = subprocess.run(['tasklist','/FO','CSV','/NH'],capture_output=True,text=True,check=True).stdout.lower()
if 'unrealeditor.exe' in processes or 'unrealeditor-cmd.exe' in processes:
    raise RuntimeError('Unreal must be closed normally before offline restore; no process was stopped.')
paths = ('Weapons/ApprenticeStaff20260927/QuartzAimV22/Materials/M_Staff_QuartzDenseV22.uasset',
         'UI/GunsmithWorkbench/M_StaffQuartzPreviewV23.uasset')
for relative in paths:
    if not (ROOT/'Before/Content'/relative).is_file():
        raise RuntimeError('Missing original material package '+relative)
for relative in paths:
    shutil.copy2(ROOT/'Before/Content'/relative,PROJECT/'Content'/relative)
receipt_path = ROOT/'install-receipt.json'
receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
receipt['complete'] = False
receipt['restored_pre_v36_materials'] = True
receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('STAFF_QUARTZ_V36_ORIGINAL_MATERIALS_RESTORED')
