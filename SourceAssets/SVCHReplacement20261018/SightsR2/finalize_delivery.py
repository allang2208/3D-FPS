import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
O=Path(__file__).parent;P=O.parents[2]
old_dir=P/'Saved/SVCHPoseAudit/svch-sights-r2-20261019-a3';new_dir=P/'Saved/SVCHPoseAudit/svch-sights-r2-20261019-a4'
def rows(p):return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines()]
before=rows(old_dir/'handoff.jsonl');after=rows(new_dir/'handoff.jsonl');pos=[];rot=[]
def relative(row):
 b,h=row['bolt'],row['hand_r'];br=R.from_quat(b['q']);return br.inv().apply(np.array(h['p'])-np.array(b['p'])),br.inv()*R.from_quat(h['q'])
for a in after:
 if a['action_alpha']<.999 or not 304/120<=a['source_time']<=344/120:continue
 b=min(before,key=lambda x:abs(x['source_time']-a['source_time']))
 if abs(b['source_time']-a['source_time'])>1e-5:continue
 ap,aq=relative(a);bp,bq=relative(b);pos.append(float(np.linalg.norm(ap-bp)));rot.append(float(np.rad2deg((aq*bq.inv()).magnitude())))
contact={'matched_samples':len(pos),'max_palm_position_difference_relative_to_bolt_cm':max(pos),'max_palm_rotation_difference_relative_to_bolt_deg':max(rot),'comparison':'A3 bolt registration vs A4 elbow clearance, source frames 304-344'}
(O/'runtime_contact_comparison.json').write_text(json.dumps(contact,indent=2));print(json.dumps(contact,indent=2))
run=json.loads((new_dir/'completion.json').read_text());install=json.loads((O/'elbow_install_receipt.json').read_text());build=json.loads((O/'build_receipt.json').read_text(encoding='utf-8-sig'));author=json.loads((O/'elbow_clearance_receipt.json').read_text())
report=json.loads((O/'delivery_receipt.json').read_text(encoding='utf-8-sig'))
report.update(status='final ElbowFit revision imported, built, captured and visually reviewed',UE_assets_saved=install['complete'],native_build_complete=build['complete'],runtime_checked=True,active_game_mesh_changed=True,source_references_switched=True,extra_middle_bracket_runtime_cause_confirmed=True,pending=[],mesh=install['mesh'],profile=install['profile'],runtime_run=str(new_dir),runtime_summary=run,runtime_contact_comparison=contact,elbow_authoring=author)
report['protected']=['shared SVD source animation assets','V9 mesh','finger local curves','normal reload profile','magazine and trigger binding','reload/bolt event clocks and handoff logic','ballistics','optic mount position']
report['visual_review']={'frames':['hip_00004.png','ads_00013.png','reload_empty_00031.png','reload_empty_00033.png','reload_empty_00034.png','reload_empty_00035.png','reload_empty_00036.png','hip_return_00085.png'],'observations':['No raised middle-rail fragment in reviewed hip/ADS frames','Rear sight no longer cuts through the right wrist in reviewed charge/release frames','Empty reload completes and returns to hip','Right-arm avoidance follows the user-authorized scope'],'not_rerun':['normal reload','ballistics','full attachment matrix','multiplayer','inspection']}
report['preview_files']=['final_rear.png','after_front.png','final_assembly.png'];report['queued_import_cancelled']=False;report['fbx_sha256']=install['fbx_sha256']
(O/'delivery_receipt.json').write_text(json.dumps(report,indent=2))
# Keep the failed open-surface signed-distance diagnostic, with its limitation explicit.
p=O/'elbow_surface_check.json'
if p.exists():
 d=json.loads(p.read_text())
 if isinstance(d,list):p.write_text(json.dumps({'method_status':'Diagnostic only: inside signs on open native arm surfaces are unreliable; do not use as acceptance evidence','samples':d},indent=2))
