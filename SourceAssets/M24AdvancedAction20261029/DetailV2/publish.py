"""Publish the saved revision and keep the established importer on this source."""
import json,runpy,shutil
from pathlib import Path
O=Path(__file__).resolve().parent;BASE=O.parent
receipt=json.loads((O/'install_receipt.json').read_text(encoding='utf-8-sig'))
if not receipt['complete']:raise RuntimeError('Finish the saved asset import first')
before=O/'Before/install-body-only.py'
if not before.exists():shutil.copy2(BASE/'install.py',before)
(BASE/'install.py').write_text('"""Active M24 body import: DetailV2. Previous importer is archived in DetailV2/Before."""\n'
    'import runpy,shutil\nfrom pathlib import Path\n'
    'O=Path(__file__).resolve().parent\n'
    'runpy.run_path(str(O/"DetailV2/install.py"),run_name="__main__")\n'
    'shutil.copy2(O/"DetailV2/install_receipt.json",O/"install_receipt.json")\n',encoding='utf-8')
shutil.copy2(O/'install_receipt.json',BASE/'install_receipt.json')
runpy.run_path(str(BASE/'register.py'),run_name='__main__')
catalog=json.loads((BASE/'catalog_receipt.json').read_text())
status=dict(complete=bool(receipt['complete'] and catalog['complete']),revision='DetailV2',weapon='ue_m24',
    id='m24_advanced_action',scope='receiver_and_handguard_only',published=True,source=str(O/'M24_AdvancedAction_DetailV2.blend'),
    runtime_mesh='/Game/Weapons/M24/AdvancedAction20261029/Meshes/SM_M24_m24_advanced_action',
    original_stock_retained=True,host_modified=False,animations_changed=False,stats_changed=False,
    cpp_changed=False,dll_rebuild_required=False,editor_opened=False,headless_import=receipt['headless_import'],
    runtime_tested=False,saved_asset_count=len(receipt['saved']),triangles=receipt['triangles'],pending=None)
for p in (O/'delivery-status.json',BASE/'delivery-status.json'):p.write_text(json.dumps(status,indent=2),encoding='utf-8')
print('M24_DETAIL_V2_PUBLISHED',json.dumps(status),flush=True)
