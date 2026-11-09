"""Smooth elbow directions on their reachable circles, preserving both endpoints."""
from pathlib import Path
import pickle,json,numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation
r=Path(__file__).parent;g=pickle.load(open(r/'geometry.pkl','rb'));ix={n:i for i,n in enumerate(g['names'])};out={}
for key,d in pickle.load(open(r/'candidate_world.pkl','rb')).items():
    w=d['world'];a,e,h=[w[:,ix[n],:3,3] for n in ('upperarm_l','lowerarm_l','hand_l')]
    axis=h-a;dist=np.linalg.norm(axis,axis=1);axis/=dist[:,None];la=np.linalg.norm(e-a,axis=1);lb=np.linalg.norm(h-e,axis=1);along=(la*la-lb*lb+dist*dist)/(2*dist);c=a+axis*along[:,None]
    pole=e-c;pole/=np.linalg.norm(pole,axis=1)[:,None]
    # Smooth signed angles in a transported frame: averaging opposing pole
    # vectors can collapse their length and recreate the elbow flip.
    reference=np.empty_like(pole);reference[0]=pole[0]
    for i in range(1,len(axis)):
        cross=np.cross(axis[i-1],axis[i]);s=np.linalg.norm(cross);cosa=np.clip(axis[i-1]@axis[i],-1,1)
        delta=Rotation.from_rotvec(cross/s*np.arctan2(s,cosa)).as_matrix() if s>1.e-10 else np.eye(3)
        reference[i]=delta@reference[i-1];reference[i]-=axis[i]*(axis[i]@reference[i]);reference[i]/=np.linalg.norm(reference[i])
    yaw=np.unwrap(np.arctan2(np.einsum('ij,ij->i',axis,np.cross(reference,pole)),np.einsum('ij,ij->i',reference,pole)))
    smooth=gaussian_filter1d(yaw,10.,mode='nearest')
    t=d['times'];alpha=np.minimum(np.clip(t/.16,0,1),np.clip((t[-1]-t)/.2,0,1));yaw=alpha*smooth+(1-alpha)*yaw
    p=Rotation.from_rotvec(axis*yaw[:,None]).apply(reference)
    out[key]=p
with (r/'pole_plan.pkl').open('wb') as f:pickle.dump(out,f)
roll={}
for family,allrows in json.loads((r/'twist_log.json').read_text()).items():
    for role,rows in [('reload',allrows[:457]),('reload_empty',allrows[457:])]:
        a=np.array(rows);phi=a[:,1];extra=phi-np.clip(phi,-np.radians(110),np.radians(110));smooth=gaussian_filter1d(extra,10.,mode='nearest');t=a[:,0];alpha=np.minimum(np.clip(t/.16,0,1),np.clip((t[-1]-t)/.2,0,1));roll[role+'_'+family]=alpha*smooth+(1-alpha)*extra
with (r/'roll_plan.pkl').open('wb') as f:pickle.dump(roll,f)
print('CONTINUOUS_ELBOW_CIRCLE_PLAN_SAVED')
