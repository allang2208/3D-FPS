import json,numpy as np,hashlib
from pathlib import Path
O=Path(__file__).parent;payload=(O/'authored_body.json').read_bytes();data=json.loads(payload);f=np.array(data['frames']);rows=json.loads((O/'body_fit.json').read_text());names=data['names']
q=f[:,:,3:7];angles=np.rad2deg(2*np.arccos(np.clip(np.abs(np.sum(q[1:]*q[:-1],axis=2)),0,1)))
ix=[i for i,n in enumerate(names) if n.startswith(('upperarm_','lowerarm_','hand_'))];at=np.unravel_index(np.argmax(angles[:,ix]),angles[:,ix].shape)
r={'source_sha256':hashlib.sha256(payload).hexdigest(),'max_arm_local_rotation_step_deg':float(angles[:,ix][at]),'bone':names[ix[at[1]]],'time':float((at[0]+1)/60),'max_elbow_step_cm':max(float(np.linalg.norm(np.array(b['arms'][s]['elbow'])-np.array(a['arms'][s]['elbow']))) for a,b in zip(rows,rows[1:]) for s in ['l','r']),'max_wrist_step_cm':max(float(np.linalg.norm(np.array(b['arms'][s]['wrist'])-np.array(a['arms'][s]['wrist']))) for a,b in zip(rows,rows[1:]) for s in ['l','r'])}
(O/'body_continuity.json').write_text(json.dumps(r,indent=2));print(r)
