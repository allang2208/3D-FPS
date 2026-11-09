from pathlib import Path
import pickle,json,numpy as np
from scipy.spatial.transform import Rotation
r=Path(__file__).resolve().parent
def matrix(v):
    a=np.asarray(v);m=np.zeros((*a.shape[:-1],4,4));m[...,3,3]=1
    m[...,:3,:3]=Rotation.from_quat(a[...,3:7].reshape(-1,4)).as_matrix().reshape(*a.shape[:-1],3,3)*a[...,None,7:10];m[...,:3,3]=a[...,:3];return m
def rot(m):return m[...,:3,:3]/np.linalg.norm(m[...,:3,:3],axis=-2,keepdims=True)
report={}
for mode in ('RAW','COMPRESSED'):
    data=pickle.load(open(r/(mode+'_quick_melee.pkl'),'rb'));names=data['names']
    frames=np.asarray(data['frames']);w={n:matrix(frames[:,i]) for i,n in enumerate(names)}
    data0=pickle.load(open(r/(mode+'_idle.pkl'),'rb'));idle={n:matrix(np.asarray(data0['frames'])[:,i]) for i,n in enumerate(names)}
    p=np.linalg.inv(w['WPN_root'])@w['hand_r'];p0=np.linalg.inv(idle['WPN_root'])@idle['hand_r']
    dist=np.linalg.norm((w['WPN_root']@p0)[:,:3,3]-w['hand_r'][:,:3,3],axis=1)
    angle=np.degrees(Rotation.from_matrix(np.swapaxes(rot(p0),1,2)@rot(p)).magnitude())
    steps={n:float(np.degrees(Rotation.from_matrix(np.swapaxes(rot(w[n][:-1]),1,2)@rot(w[n][1:])).magnitude()).max()) for n in ['upperarm_r','lowerarm_r','lowerarm_twist_01_r','lowerarm_twist_02_r','hand_r']}
    report[mode]={'max_grip_error_cm':float(dist.max()),'max_grip_angle_deg':float(angle.max()),'worst_time':float(np.argmax(dist)/240),'joint_step_degrees_at_240hz':steps,
        'samples':[dict(t=i/240,error_cm=float(dist[i]),angle_deg=float(angle[i])) for i in range(0,len(dist),24)]}
(r/'melee_measurement.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
