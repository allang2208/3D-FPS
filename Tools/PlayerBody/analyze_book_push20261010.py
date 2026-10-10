"""Summarize the requested native-arm and actual animation-proxy diagnosis."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/ThirdPersonBookPush20261010'
data=json.loads((OUT/'authored.json').read_text())
carry=json.loads((ROOT/data['source_parent']).read_text())
base=np.asarray(carry['clips']['Staff.BookCarry']['frames'][0])
frames=np.asarray(data['clips']['Staff.BookPush']['frames'])
names=data['names'];wrist=names.index('hand_l')
def degrees(a,b):
    return np.rad2deg((R.from_quat(a)*R.from_quat(b).inv()).magnitude())
changed=[names[i] for i in range(len(names)) if np.max(degrees(frames[:,i,3:7],base[i,3:7]))>1.e-5]
report=dict(scope='Requested book-push diagnosis only; animation transforms, not rendered skin or gameplay acceptance',
    authored_frames=len(frames),changed_rotation_tracks=changed,
    max_authored_wrist_delta_degrees=float(np.max(degrees(frames[:,wrist,3:7],base[wrist,3:7]))),
    max_authored_translation_delta_cm=float(np.max(np.abs(frames[:,:,:3]-base[:,:3]))),
    max_authored_scale_delta=float(np.max(np.abs(frames[:,:,7:]-base[:,7:]))),
    endpoint_rotation_delta_degrees=float(np.max(degrees(frames[[0,-1],:,3:7].reshape(-1,4),np.tile(base[:,3:7],(2,1))))),
    gameplay_tested=False,rendered=False)
raw=json.loads((OUT/'proxy-diagnosis-final.json').read_text())
report['proxy_scope']=raw['scope'];cases={}
for case in raw['cases']:
    rows=case['samples'];local=np.array([s['local']['hand_l'] for s in rows])
    points=np.array([s['component']['hand_l'][:3] for s in rows])
    angles=degrees(local[:,3:7],base[wrist,3:7]);peak=int(np.argmax(angles))
    elbow=names.index('lowerarm_l')
    lengths=np.array([[np.linalg.norm(np.array(s['component'][b][:3])-s['component'][a][:3])
                      for a,b in [('upperarm_l','lowerarm_l'),('lowerarm_l','hand_l')]] for s in rows])
    nominal=np.array([np.linalg.norm(base[elbow,:3]),np.linalg.norm(base[wrist,:3])])
    cases[case['case']]=dict(samples=len(rows),max_wrist_delta_degrees=float(angles[peak]),
        peak_time_seconds=rows[peak]['time'],max_wrist_step_cm=float(np.max(np.linalg.norm(np.diff(points,axis=0),axis=1))),
        max_bone_length_error_cm=float(np.max(np.abs(lengths-nominal))),
        finish_wrist_delta_degrees=float(angles[-1]))
report['proxy_cases']=cases
(OUT/'diagnosis-summary-final.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
