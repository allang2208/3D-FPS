"""Save the requested repair using the existing mutually exclusive editor bridge."""
import json
import runpy
import shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
previous=PROJECT/'SourceAssets/HospitalContainers20261003/Receipts/install.json'
(ROOT/'Backup').mkdir(exist_ok=True)
saved=ROOT/'Backup/hospital-containers-install-v1.json'
if previous.exists() and not saved.exists():shutil.copy2(previous,saved)
runpy.run_path(str(PROJECT/'SourceAssets/HospitalContainers20261003/Scripts/install_scenes.py'),
    init_globals={'HOSPITAL_CONTAINERS_EXISTING_EDITOR':True},run_name='__main__')
report=json.loads(previous.read_text('utf8'))
report.update(batch='HospitalPolish20261003',assets_receipt='Receipts/assets.json',native_changes=False,
    user_requested_diagnosis='Receipts/hospital-diagnosis.json',runtime_test_run=False)
(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('HOSPITAL_POLISH_MAPS_SAVED',flush=True)
