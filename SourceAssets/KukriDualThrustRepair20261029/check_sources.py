"""Scoped native-chain checks for the third combo attack only."""
import json
import numpy as np
from scipy.spatial.transform import Rotation as R
import author as a
src=json.loads((a.OUT/'inputs.json').read_text());checks=[]
def check(name,passed,value):checks.append({'case':name,'passed':bool(passed),'value':float(value)})
for label,d in src.items():
    b=a.body_for(label,d);data=json.loads((a.OUT/(label+'-actions.json')).read_text());take=data['clips'][a.ROLE]
    f=np.array(take['frames']);base=np.array(d['clips'][a.ROLE]['frames']);p,q=b.world(f);m=a.metrics(b,f)
    check(label+'/same gameplay duration',abs((len(f)-1)/120-2.05)<1e-6,(len(f)-1)/120)
    check(label+'/same contact time',abs(take['contact']*2.05-.6)<1e-6,take['contact']*2.05)
    check(label+'/same release time',abs(take['release']*2.05-.72)<1e-6,take['release']*2.05)
    check(label+'/finite poses',np.isfinite(f).all(),np.count_nonzero(~np.isfinite(f)))
    for side in 'rl':
        h=b.ix['hand_'+side]
        check(label+'/'+side+'/wrist bend below 50 degrees',m[side]['wrist_max_deg']<50,m[side]['wrist_max_deg'])
        check(label+'/'+side+'/extended impact without locked elbow',.96<m[side]['contact_reach_ratio']<.99,m[side]['contact_reach_ratio'])
        check(label+'/'+side+'/visible extension',m[side]['reach_over_90_seconds']>.40,m[side]['reach_over_90_seconds'])
        check(label+'/'+side+'/smooth hand path',m[side]['max_hand_step_cm']<4,m[side]['max_hand_step_cm'])
        names=[n+'_'+side for n in ('upperarm','lowerarm','hand','upperarm_twist_01','upperarm_twist_02','lowerarm_twist_01','lowerarm_twist_02') if n+'_'+side in b.ix]
        i=[b.ix[n] for n in names]
        step=np.degrees((R.from_quat(f[1:,i,3:7].reshape(-1,4))*R.from_quat(f[:-1,i,3:7].reshape(-1,4)).inv()).magnitude()).max()
        check(label+'/'+side+'/no rotational frame jump',step<12,step)
        pos=np.max(abs(f[:,i,:3]-base[:,i,:3]));scale=np.max(abs(f[:,i,7:]-base[:,i,7:]))
        # Inputs are separately compressed clips; their identical native
        # translations differ by up to 0.0052 cm at the idle boundary.
        check(label+'/'+side+'/native arm translations',pos<.01,pos)
        check(label+'/'+side+'/native arm scales',scale<.001,scale)
    for endpoint in (0,-1):
        err=np.degrees((R.from_quat(f[endpoint,:,3:7])*R.from_quat(b.idle[:,3:7]).inv()).magnitude()).max()
        check(label+'/idle boundary '+str(endpoint),err<.001,err)
    separation=np.linalg.norm(p[:,b.ix['hand_l']]-p[:,b.ix['hand_r']],axis=1)
    check(label+'/separate blade hands',separation.min()>20,separation.min())
out={'checks':checks,'failures':sum(not x['passed'] for x in checks),'scope':'Offline source pose and timing checks; no gameplay or multiplayer execution'}
(a.OUT/'source-checks.json').write_text(json.dumps(out,indent=2))
print(json.dumps({'checks':len(checks),'failures':out['failures'],'failed':[x for x in checks if not x['passed']]}))
raise SystemExit(1 if out['failures'] else 0)
