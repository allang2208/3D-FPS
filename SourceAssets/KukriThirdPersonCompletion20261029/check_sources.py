"""Scoped numerical checks for joins, wrist bend and held/released blade phases."""
import json
import numpy as np
import author as a
R=a.R;rows=[]
def check(name,passed,value):
    rows.append(dict(case=name,passed=bool(passed),value=value));print('PASS' if passed else 'FAIL',name,value,flush=True)
inputs=json.loads((a.OUT/'inputs.json').read_text());present=json.loads((a.OUT/'presentation.json').read_text())
for label in ('jason','kaitlin'):
    body=a.c.Body(a.old.base.rig.DATA[label]);data=json.loads((a.OUT/(label+'-actions.json')).read_text())
    check(label+'/seven authored branches',len(data['clips'])==7,len(data['clips']))
    for role,clip in data['clips'].items():
        f=np.array(clip['frames']);p,q=body.world(f);prefix=label+'/'+role
        err=float(abs(np.linalg.norm(f[:,:,3:7],axis=2)-1).max());check(prefix+'/unit quaternions',err<1e-5,err)
        err=float(abs(f[:,:,7:]-body.ref[None,:,7:]).max());check(prefix+'/native scales',err<1e-5,err)
        for side in 'rl':
            h=body.ix['hand_'+side];e=body.ix['lowerarm_'+side]
            axis=(R.from_quat(q[:,h])*R.from_quat(body.ref[h,3:7]).inv()).apply(np.tile(a.c.unit(body.ref[h,:3]),(len(f),1)))
            bend=np.degrees(np.arccos(np.clip(np.sum(axis*a.c.unit(p[:,h]-p[:,e]),axis=1),-1,1)))
            maximum=float(bend.max());check(prefix+'/'+side+' wrist bend degrees',maximum<70,maximum)
            step=float(np.linalg.norm(np.diff(p[:,h],axis=0),axis=1).max());check(prefix+'/'+side+' maximum hand step cm at 120 Hz',step<8,step)
        idle_role='Pistol.KukriCarry.Hip' if role.startswith('Pistol') else 'Kukri.FullBody.Dual.Idle' if '.Dual.' in role else 'Kukri.FullBody.Idle'
        idle=np.array(inputs[label]['clips'][idle_role]['frames'][0]);end=f[0] if role.endswith('.Run') else f[-1]
        angle=float(np.degrees((R.from_quat(end[:,3:7])*R.from_quat(idle[:,3:7]).inv()).magnitude()).max())
        distance=float(np.linalg.norm(end[:,:3]-idle[:,:3],axis=1).max());check(prefix+'/carry join',angle<.02 and distance<.01,dict(degrees=angle,cm=distance))
    for role,take in present[label].items():
        for side,keys in take['blades'].items():
            keys=np.array(keys);angle=R.from_quat(keys[[0,-1],3:]).magnitude();distance=np.linalg.norm(keys[[0,-1],:3],axis=1)
            check(label+'/'+role+'/'+side+' mounted at both boundaries',angle.max()<1e-5 and distance.max()<1e-5,dict(cm=float(distance.max()),degrees=float(np.degrees(angle.max()))))
result=dict(checks=rows,failures=sum(not r['passed'] for r in rows),scope='Offline native author joins and blade mounts; not gameplay or UDP validation')
(a.OUT/'source-checks.json').write_text(json.dumps(result,indent=2));print('SOURCE_CHECKS',len(rows),'FAILURES',result['failures'])
raise SystemExit(1 if result['failures'] else 0)
