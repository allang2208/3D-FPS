"""Keep R4 contacts; redistribute inspection forearm twist on SVCH only."""
import copy,json
import numpy as np
from scipy.spatial.transform import Rotation as Rot,Slerp
from diagnose_wrist import O,D,N,PI,R,clip,profile,corrected,metric,rot,axis,rest,H,T1,T2
out=copy.deepcopy(profile)
entry=next(c for c in out['clips'] if c['base']==clip['path'])
poses=[corrected(i)[1] for i in range(len(clip['frames']))]
rolls=np.degrees(np.unwrap(np.radians([metric(p)['hand_roll_deg'] for p in poses])))
def smooth(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)
newposes=[p.copy() for p in poses]
for bone,share in ((T1,1.),(T2,.5)):
    values=[]
    prior=next((t for t in entry['tracks'] if t['bone']==N[bone]),None)
    for i,(p,roll) in enumerate(zip(poses,rolls)):
        t=min(i/120,clip['duration']);weight=smooth(t/.45)*(1-smooth((t-5.25)/.55))
        local=rot(p[PI[bone]]).inv()*rot(p[bone])
        target=Rot.from_rotvec(axis*np.radians(share*roll))*rest[bone]
        q=Slerp([0,1],Rot.from_quat([local.as_quat(),target.as_quat()]))(weight)
        base=Rot.from_quat(np.asarray(clip['frames'][i])[bone,3:7])
        delta=(q*base.inv()).as_quat()
        if weight==0:
            delta=np.array([0,0,0,1.]) if prior is None else np.array(prior['values']).reshape(-1,10)[np.abs(np.array(prior['times'])-t).argmin(),3:7]
        if values and delta@np.asarray(values[-1][3:7])<0:delta=-delta
        values.append([0,0,0,*delta,0,0,0])
        scale=np.linalg.norm(p[bone,:3,:3],axis=0)
        if weight>0:newposes[i][bone,:3,:3]=(rot(p[PI[bone]])*q).as_matrix()*scale
    entry['tracks']=[track for track in entry['tracks'] if track['bone']!=N[bone]]
    entry['tracks'].append({'bone':N[bone],'times':[min(i/120,clip['duration']) for i in range(len(values))],
                          'values':np.round(np.asarray(values),9).ravel().tolist()})
peak=round(3.716667*120)
report={'changed_clip':clip['path'],'changed_bones':[N[T1],N[T2]],'shares':[1,.5],
    'peak_before':metric(poses[peak]),'peak_after':metric(newposes[peak]),
    'max_hand_transform_change':float(max(np.abs(a[H]-b[H]).max() for a,b in zip(poses,newposes))),
    'endpoint_matrix_change':float(max(np.abs(newposes[i]-poses[i]).max() for i in (0,len(poses)-1))),
    'other_clips_unchanged':all(c==p for c,p in zip(out['clips'],profile['clips']) if c['base']!=clip['path'])}
(O/'shared_profile_r5.json').write_text(json.dumps(out,separators=(',',':')))
(O/'profile_receipt_r5.json').write_text(json.dumps(report,indent=1))
print(json.dumps(report,indent=1))
