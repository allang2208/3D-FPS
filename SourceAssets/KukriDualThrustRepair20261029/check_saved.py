import json
import numpy as np
from scipy.spatial.transform import Rotation as R
import author as a
saved=json.loads((a.OUT/'saved-poses.json').read_text());source=json.loads((a.OUT/'inputs.json').read_text());checks=[]
for label,d in saved.items():
    expected=json.loads((a.OUT/(label+'-actions.json')).read_text())['clips'][a.ROLE]
    take=d['clips'][a.ROLE];x=np.array(expected['frames']);y=np.array(take['frames']);b=a.body_for(label,source[label])
    angle=np.degrees((R.from_quat(x[:,:,3:7].reshape(-1,4))*R.from_quat(y[:,:,3:7].reshape(-1,4)).inv()).magnitude()).max()
    position=np.max(np.abs(x[:,:,:3]-y[:,:,:3]));met=a.metrics(b,y)
    markers=take['markers'];passed=angle<.35 and position<.015 and take['skeleton_matches'] and abs(markers['Contact']-.6)<1e-5 and abs(markers['Release']-.72)<1e-5 and 'NativeSwordGrip' in markers
    checks.append({'body':label,'passed':bool(passed),'source_rotation_error_degrees':float(angle),'source_position_error_cm':float(position),'markers':markers,'metrics':met})
out={'checks':checks,'failures':sum(not c['passed'] for c in checks),'scope':'Saved UE compressed assets, not final gameplay graph'}
(a.OUT/'saved-checks.json').write_text(json.dumps(out,indent=2));print(json.dumps({'checks':len(checks),'failures':out['failures'],'max_rotation_error_degrees':max(c['source_rotation_error_degrees'] for c in checks)}))
raise SystemExit(1 if out['failures'] else 0)
