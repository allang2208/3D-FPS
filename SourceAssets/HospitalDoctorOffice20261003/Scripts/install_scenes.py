"""Save the accepted hospital sample and formal randomized dungeon; no gameplay run."""
import json,runpy,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
build=json.loads((ROOT/'Receipts/native-build.json').read_text('utf-8-sig'))
if build.get('stage')!='binaries_saved':raise RuntimeError('Preserve maps until this native repair is built')
existing=globals().get('HOSPITAL_OFFICE_EXISTING_EDITOR',False)
receipt=PROJECT/'SourceAssets/HospitalContainers20261003/Receipts/install.json'
backup=ROOT/'Backup/previous-hospital-install.json'
if receipt.exists() and not backup.exists():shutil.copy2(receipt,backup)
runpy.run_path(str(PROJECT/'SourceAssets/HospitalContainers20261003/Scripts/install_scenes.py'),
 init_globals={'HOSPITAL_CONTAINERS_EXISTING_EDITOR':existing},run_name='__main__')
report=json.loads(receipt.read_text('utf8'))
report.update(batch='HospitalDoctorOffice20261003',native_build=build,office_containers=3,
 bedside_body_repair='Set mobility before assigning the body mesh',bedside_placement='wall bays',
 assets_receipt='Receipts/assets.json',runtime_test_run=False)
(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
line_path=PROJECT/'SourceAssets/DungeonHospitalLine20261003/Config/line.json'
line=json.loads(line_path.read_text('utf8'))
line.update(hospital_doctor_office_revision=1,hospital_office_container_count=3,
 hospital_office_furniture_count=10,hospital_ward_detail_revision=1)
line_path.write_text(json.dumps(line,ensure_ascii=False,indent=2),encoding='utf8')
print('HOSPITAL_DOCTOR_OFFICE_MAPS_SAVED',flush=True)
