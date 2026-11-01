import json,runpy,shutil
from pathlib import Path
O=Path(__file__).resolve().parent;BASE=O.parent
r=json.loads((O/'install_receipt.json').read_text(encoding='utf-8-sig'))
build=json.loads((BASE/'build-receipt.json').read_text(encoding='utf-8-sig'))
if not r['complete'] or not build['complete']:raise RuntimeError('Finish saved assets and DLL first')
before=O/'Before/install-detail-v2.py'
if not before.exists():shutil.copy2(BASE/'install.py',before)
(BASE/'install.py').write_text('"""Active M24 front chassis: FullBodyV3."""\n'
    'import runpy,shutil\nfrom pathlib import Path\nO=Path(__file__).resolve().parent\n'
    'runpy.run_path(str(O/"FullBodyV3/install.py"),run_name="__main__")\n'
    'shutil.copy2(O/"FullBodyV3/install_receipt.json",O/"install_receipt.json")\n',encoding='utf-8')
shutil.copy2(O/'install_receipt.json',BASE/'install_receipt.json')
runpy.run_path(str(BASE/'register.py'),run_name='__main__')
fit=json.loads((O/'bipod-fit.json').read_text())
status=dict(complete=True,revision='FullBodyV3',weapon='ue_m24',id='m24_advanced_action',
    scope='full front chassis; original buttstock retained',published=True,
    source=str(O/'M24_AdvancedAction_FullBodyV3.blend'),
    runtime_mesh='/Game/Weapons/M24/AdvancedAction20261029/Meshes/SM_M24_m24_advanced_action',
    host_modified=True,native_front_faces=r['native_front_face_count'],
    original_stock_retained=True,animations_changed=False,stats_changed=False,
    bipod_base=r['bipod_base'],bipod_leg_meshes_changed=False,bipod_duration=.48,
    cpp_changed=True,dll_saved=True,editor_opened=False,runtime_tested=False,
    bipod_contact_gap=fit['open_gap_in_new_mount'],saved_asset_count=len(r['saved']),pending=None)
for p in (O/'delivery-status.json',BASE/'delivery-status.json'):p.write_text(json.dumps(status,indent=2),encoding='utf-8')
print('M24_FULL_BODY_V3_SAVED',len(r['saved']),flush=True)
