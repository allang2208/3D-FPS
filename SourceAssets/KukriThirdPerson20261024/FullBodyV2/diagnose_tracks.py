"""Requested diagnosis: compare donor/retarget/authoring leg motion per action."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent;BASE=OUT.parent
raw=json.loads((BASE/'retargeted-poses.json').read_text())
auth=json.loads((BASE/'adapted-actions.json').read_text())
ix={n:i for i,n in enumerate(raw['names'])};parents=raw['parents']
def world(frames):
    f=np.asarray(frames);p=f[:,:,:3].copy();q=f[:,:,3:7].copy();s=f[:,:,7:].copy()
    for i,par in enumerate(parents):
        if par<0:continue
        p[:,i]=p[:,par]+R.from_quat(q[:,par]).apply(f[:,i,:3]*s[:,par])
        q[:,i]=(R.from_quat(q[:,par])*R.from_quat(q[:,i])).as_quat();s[:,i]*=s[:,par]
    return p,q
def measure(c):
    p,q=world(c['frames']);out={}
    for side in 'lr':
        hip,knee,ankle=[p[:,ix[n+'_'+side]] for n in ('thigh','calf','foot')]
        a=hip-knee;b=ankle-knee
        angle=np.rad2deg(np.arccos(np.clip(np.sum(a*b,axis=1)/np.linalg.norm(a,axis=1)/np.linalg.norm(b,axis=1),-1,1)))
        flex=180-angle
        out[side]=dict(knee_flex_min=round(float(flex.min()),2),knee_flex_max=round(float(flex.max()),2),
          ankle_range_cm=np.ptp(ankle,axis=0).round(2).tolist(),
          knee_rotation_range_deg=round(float(np.rad2deg((R.from_quat(np.asarray(c['frames'])[:,ix['calf_'+side],3:7])*R.from_quat(np.asarray(c['frames'])[0,ix['calf_'+side],3:7]).inv()).magnitude()).max()),2))
    out['pelvis_range_cm']=np.ptp(p[:,ix['pelvis']],axis=0).round(2).tolist()
    out['hand_range_cm']=np.ptp(p[:,ix['hand_r']],axis=0).round(2).tolist()
    return out
report=dict(raw={k:measure(v) for k,v in raw['clips'].items()},authored={k:measure(v) for k,v in auth['clips'].items()})
(OUT/'tracks-before.json').write_text(json.dumps(report,indent=2))
for kind,clips in report.items():
    for k,v in clips.items():
        print(kind,k,'knees',[(v[s]['knee_flex_min'],v[s]['knee_flex_max']) for s in 'lr'],'hip',v['pelvis_range_cm'],'feet',[v[s]['ankle_range_cm'] for s in 'lr'])
