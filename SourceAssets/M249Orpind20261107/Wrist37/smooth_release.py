"""Smooth elbow-plane movement, keeping the right hand's full contact transform."""
from held import *
from scipy.ndimage import gaussian_filter1d
poses=pickle.load(open(HERE/'right.pkl','rb'))
source=pickle.load(open(ROOT/'current_poses.pkl','rb'))['base']
c,u,e,h,arms,hands=indices('r');report={}
for path,old in poses.items():
    t=source[path]['times'];offset=.9 if path.endswith('_empty') else 0
    desired=gaussian_filter1d(old[:,e,:3,3],3.5,axis=0,mode='nearest')
    strength=ease((t-(4.90-offset))/.12)*(1-ease((t-(5.50-offset))/.12))
    new=old.copy()
    for k,w in enumerate(old):
        if strength[k]<=0:continue
        a0,e0,h0=[w[i,:3,3] for i in [u,e,h]];axis=unit(h0-a0);center=a0+axis*((e0-a0)@axis)
        oldpole=unit(e0-center);target=unit(desired[k]-center-axis*((desired[k]-center)@axis))
        angle=np.arctan2(axis@np.cross(oldpole,target),oldpole@target)*strength[k]
        new[k]=solve(w,[0,0,0,angle],'r',station_weight=0.)
    new=preserve_local(old,new,[u,e,h]+arms)
    poses[path]=new;step=np.linalg.norm(np.diff(new[:,e,:3,3],axis=0),axis=1)
    report[path]=dict(elbow_step_cm=float(step.max()),hand_change_cm=float(np.linalg.norm(new[:,h,:3,3]-old[:,h,:3,3],axis=1).max()))
    print(path,report[path],flush=True)
pickle.dump(poses,open(HERE/'right_smooth.pkl','wb'));(HERE/'right_release.json').write_text(json.dumps(report,indent=2))
