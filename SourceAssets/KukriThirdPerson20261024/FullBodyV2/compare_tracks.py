"""Requested per-role check of knee compliance, steps and phase handoffs."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
OUT=Path(__file__).resolve().parent
data=json.loads((OUT/'adapted-actions.json').read_text());names=data['names'];parents=data['parents'];ix={n:i for i,n in enumerate(names)}
def world(f):
    f=np.asarray(f);p=f[:,:,:3].copy();q=f[:,:,3:7].copy();s=f[:,:,7:].copy()
    for i,par in enumerate(parents):
        if par<0:continue
        p[:,i]=p[:,par]+R.from_quat(q[:,par]).apply(f[:,i,:3]*s[:,par]);q[:,i]=(R.from_quat(q[:,par])*R.from_quat(q[:,i])).as_quat();s[:,i]*=s[:,par]
    return p
report={};poses={}
for role,c in data['clips'].items():
    p=world(c['frames']);poses[role]=p;row={}
    for side in 'lr':
        h,k,a=[p[:,ix[n+'_'+side]] for n in ('thigh','calf','foot')];v=h-k;w=a-k
        flex=180-np.rad2deg(np.arccos(np.clip(np.sum(v*w,axis=1)/np.linalg.norm(v,axis=1)/np.linalg.norm(w,axis=1),-1,1)))
        row[side]=dict(knee_flex_min=float(flex.min()),knee_flex_max=float(flex.max()),ankle_range_cm=np.ptp(a,axis=0).tolist())
    report[role]=row
seams={}
for a,b in [('Charge','Heavy'),('Whirlwind.Start','Whirlwind.Loop'),('Whirlwind.Loop','Whirlwind.End')]:
    seams[a+' -> '+b]={n:float(np.linalg.norm(poses[a][-1,ix[n]]-poses[b][0,ix[n]])) for n in ('pelvis','foot_l','foot_r','hand_r')}
(OUT/'tracks-after.json').write_text(json.dumps(dict(roles=report,seams_cm=seams),indent=2))
print('roles',len(report),'lowest knee flex',min(r[s]['knee_flex_min'] for r in report.values() for s in 'lr'))
print('spin feet ranges',report['Whirlwind.Loop'])
print('seams',seams)
